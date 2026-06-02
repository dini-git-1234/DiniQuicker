from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError, async_playwright

from report_steps.generic_image_to_table import get_table_from_image
from report_steps.taba_results_table import get_table_from_images
from report_steps.taba_text_extractor import generate_property_report
from utils.temp_paths import temp_dir

print("📦 report_steps/download_taba.py נטען", flush=True)

DOWNLOAD_DIR = temp_dir("taba", "downloads")
DEBUG_DIR = temp_dir("taba", "debug")


EXTRA_TABA_PLANS_INSTRUCTIONS = """
התייחס לטבלת התכניות המופיעה בתמונה (תב״ע).
כל שורה בטבלה מייצגת תכנית אחת, כולל מספר תכנית, שם/מטרה, סטטוס ותאריכים רלוונטיים אם קיימים.
שמור על סדר עמודות ברור, והקפד שכל התוכן הטבלאי יופיע במבנה headers ו-rows בלבד ללא טקסט נוסף.
"""

EXTRA_PLANNING_RIGHTS_INSTRUCTIONS = """
התייחס לטבלת זכויות בנייה עבור הנכס.
חלץ רק שורות המכילות ערך מספרי או כמותי כולל יחידת המידה שלו (למשל: "קו בנין: 5", "תכסית: 40%").
הקפד שסדר העמודות יהיה: [סוג הזכות, זיהוי/ערך, תיאור / הערות].
בעמודת "תיאור / הערות" יש לכלול, ככל האפשר, את מספר התכנית הרלוונטית (למשל: "836/מ/במ").
"""


@dataclass(frozen=True)
class TabaTablesResult:
    plans_table: dict | None
    rights_table: dict | None
    plans_image_path: str | None = None
    rights_image_path: str | None = None
    pdf_files: list[Path] | None = None


def _safe_table(table: Any) -> dict | None:
    if isinstance(table, dict) and table.get("rows"):
        return table
    return None


# -----------------------------
# 1) הורדה מרמ"י (PDF + טבלת תוצאות מהאתר)
# -----------------------------
async def download_taba_pdfs(
    gush: str,
    helka: str,
    output_dir: Path | None = None,
) -> dict:
    """מוריד קבצי תב״ע (PDF) מרמ״י לפי גוש/חלקה, ומנסה גם לחלץ טבלת תכניות מהאתר."""
    if output_dir is None:
        output_dir = DOWNLOAD_DIR
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    downloaded_files: list[Path] = []
    screenshot_paths: list[Path] = []
    print(f"🚀 התחלת הורדת תב״ע: גוש {gush}, חלקה {helka}")

    async with async_playwright() as p:
        print("🧠 מפעיל דפדפן")
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        print("🌐 נכנס לאתר")
        await page.goto(
            "https://apps.land.gov.il/TabaSearch/#/Plans",
            wait_until="domcontentloaded",
        )

        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=DEBUG_DIR / "01_loaded_site.png")

        gush_box = page.locator("#Gush")
        helka_box = page.locator("#Chelka")
        if await gush_box.count() == 0 or await helka_box.count() == 0:
            await page.screenshot(path=DEBUG_DIR / "fields_not_found.png")
            raise RuntimeError("❌ לא נמצאו שדות גוש / חלקה לפי id")

        print(f"✍️ ממלא גוש: {gush}")
        await gush_box.click()
        await gush_box.fill(str(gush))

        print(f"✍️ ממלא חלקה: {helka}")
        await helka_box.click()
        await helka_box.fill(str(helka))

        await page.screenshot(path=DEBUG_DIR / "02_filled_search.png")

        try:
            await helka_box.press("Enter")
            await page.wait_for_timeout(8_000)
        except Exception:
            pass

        # --- ניסיון לחלץ טבלת תכניות דרך צילום מקטעים ו-Gemini ---
        planning_table = None
        try:
            print("⏳ מתחיל תהליך צילום במקטעים...")
            scroll_selector = ".section-scrollable-container"
            await page.wait_for_selector(scroll_selector, timeout=30_000)

            dimensions = await page.evaluate(
                """
                (selector) => {
                    const el = document.querySelector(selector);
                    return {
                        height: el ? el.clientHeight : 0,
                        scrollHeight: el ? el.scrollHeight : 0
                    };
                }
                """,
                scroll_selector,
            )

            viewport_height = int(dimensions.get("height") or 0)
            total_height = int(dimensions.get("scrollHeight") or 0)
            current_scroll = 0
            count = 1

            if viewport_height > 0 and total_height > 0:
                while current_scroll < total_height:
                    print(f"📸 מצלם מקטע {count}...")
                    await page.evaluate(
                        """
                        (data) => {
                            const el = document.querySelector(data.selector);
                            if (el) {
                                el.scrollTop = data.scrollAmount;
                            }
                        }
                        """,
                        {"selector": scroll_selector, "scrollAmount": current_scroll},
                    )
                    await page.wait_for_timeout(1500)

                    table_locator = page.locator("app-plans-result")
                    path = DEBUG_DIR / f"part_{count}_{gush}_{helka}.png"
                    await table_locator.screenshot(path=path)
                    screenshot_paths.append(path)

                    current_scroll += viewport_height
                    count += 1
                    total_height = await page.evaluate(
                        "(sel) => document.querySelector(sel).scrollHeight",
                        scroll_selector,
                    )

            if screenshot_paths:
                print("🧠 שולח את צילומי המסך ל-Gemini לחילוץ טבלה...")
                planning_table = await get_table_from_images([str(p) for p in screenshot_paths])
        except Exception as e:
            print(f"⚠️ שגיאה בעיבוד טבלת התכניות מהאתר: {e}")

        # --- הורדת קבצי PDF ---
        print("⏳ ממתין לקישורי הורדה")
        await page.wait_for_selector("a", timeout=25_000)

        rows = page.locator("app-plans-result-row")
        download_links = rows.locator(
            "div:has(span:text-is('הוראות')) a[href*='takanonim'][href$='.pdf']"
        )

        link_count = await download_links.count()
        print(f"📎 נמצאו {link_count} קישורי הורדה")
        if link_count == 0:
            await page.screenshot(path=DEBUG_DIR / "no_download_links.png")
            raise RuntimeError("❌ לא נמצאו קישורי הורדה")

        for i in range(link_count):
            link = download_links.nth(i)
            print(f"⬇️ מוריד קובץ {i + 1}/{link_count}")
            try:
                async with page.expect_download(timeout=15_000) as download_info:
                    await link.click()
                download = await download_info.value
            except TimeoutError:
                print("⚠️ לא הופעל download")
                continue

            file_path = output_dir / download.suggested_filename
            await download.save_as(file_path)
            downloaded_files.append(file_path)
            print(f"✅ הורד: {file_path.name}")

        await browser.close()
        print(f"🏁 סיום – ירדו {len(downloaded_files)} קבצים")
        return {
            "pdf_files": downloaded_files,
            "planning_table": planning_table,
        }


# -----------------------------
# 2) Scraper עירייה (תמונות טבלאות)
# -----------------------------
SCREENSHOT_DIR: Path | None = None


def _ensure_screenshot_dir() -> None:
    if SCREENSHOT_DIR is None:
        return
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


async def _take_screenshot(page, name: str, full_page: bool = False) -> None:
    if SCREENSHOT_DIR is None:
        return
    _ensure_screenshot_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = SCREENSHOT_DIR / f"{timestamp}_{name}.png"
    await page.screenshot(path=str(path), full_page=full_page)
    print(f"📸 נשמר צילום מסך: {path}")


def _get_link_from_file(city_name: str) -> str | None:
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "city_link.json")
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        for entry in data:
            if entry.get("name") == city_name or entry.get("alias") == city_name:
                return entry.get("link")
    except Exception:
        return None
    return None


async def _select_gush_helka_universal(page) -> None:
    keywords = ["גוש", "חלקה", "מקרקעין"]

    labels = page.locator("label")
    for i in range(await labels.count()):
        label = labels.nth(i)
        text = (await label.inner_text()).replace("\n", " ").strip()
        if any(k in text for k in keywords):
            radio = label.locator("input[type=radio], input[type=checkbox]")
            if await radio.count() > 0:
                await radio.first.check()
                print(f"✔ נבחר רדיו לפי label: {text}")
                return

    tabs = page.locator('[role="tab"]')
    for i in range(await tabs.count()):
        tab = tabs.nth(i)
        text = (await tab.inner_text()).replace("\n", " ").strip()
        if any(k in text for k in keywords):
            await tab.click()
            print(f"✔ נבחר tab לפי טקסט: {text}")
            return


async def run_scraper(city_name: str, gush_val: str, helka_val: str, base_path: str) -> tuple[str | None, str | None]:
    global SCREENSHOT_DIR
    SCREENSHOT_DIR = Path(base_path) / "screenshots" / "taba"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    table_path: str | None = None
    rights_path: str | None = None
    url = _get_link_from_file(city_name)
    print("URL:", url)
    if url is None or not str(url).startswith("http"):
        return None, None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print(f"ניווט לכתובת: {url}")
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            try:
                await page.wait_for_selector("#GushNumber", timeout=30000)
            except Exception:
                print("⚠️ שדה #GushNumber לא נטען בזמן, ממשיך עם מצב העמוד הנוכחי.")

            await _take_screenshot(page, "01_initial_load", True)

            # פופאפ אישור
            try:
                confirm_btn = page.locator(
                    'button:has-text("אשר וסגור"), button:has-text("אני מסכים")'
                ).first
                if await confirm_btn.is_visible(timeout=3000):
                    await confirm_btn.click()
                    print("מסך אישור נסגר.")
                    await _take_screenshot(page, "02_after_popup_close")
            except Exception:
                print("לא נמצא מסך אישור")

            await _select_gush_helka_universal(page)
            await _take_screenshot(page, "03_after_select_gush_helka")

            print(f"מזין גוש: {gush_val}, חלקה: {helka_val}")
            await page.fill("#GushNumber", str(gush_val))
            await _take_screenshot(page, "04_after_fill_gush")
            await page.fill("#GushHelka", str(helka_val))
            await _take_screenshot(page, "05_after_fill_helka")

            await page.click("#btnShow")
            print("לחיצה על כפתור הצג")
            await page.wait_for_timeout(2000)
            await _take_screenshot(page, "06_after_show_click", True)

            internal_link_selector = 'a:has(span.glyphicon-new-window)'
            await page.wait_for_selector(internal_link_selector, timeout=10000)
            await _take_screenshot(page, "07_link_ready")

            await page.click(internal_link_selector)
            await page.wait_for_timeout(2000)
            await _take_screenshot(page, "08_after_first_link_click", True)

            target_purpose = "מגורים"
            alternative_purpose = "בניני ציבור"
            try:
                rows = page.locator("table#results-table tbody tr")
                row_count = await rows.count()
                clicked = False
                for i in range(row_count):
                    row = rows.nth(i)
                    purpose_text = await row.locator("td:nth-child(7)").inner_text()
                    if target_purpose in purpose_text or alternative_purpose in purpose_text:
                        print(f"נמצאה שורה מתאימה עם יעוד: {purpose_text}. לוחץ...")
                        await row.locator('a:has(span.glyphicon-new-window)').click()
                        clicked = True
                        break
                if not clicked and row_count > 0:
                    print("לא נמצא יעוד ספציפי, לוחץ על האופציה הראשונה כברירת מחדל.")
                    await rows.first.locator('a:has(span.glyphicon-new-window)').click()
            except Exception as e:
                print(f"שגיאה בניסיון בחירת שורה מהטבלה: {e}")

            await page.wait_for_timeout(2000)
            await _take_screenshot(page, "08_after_smart_link_click", True)

            try:
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            await _take_screenshot(page, "10_final_result_full", True)

            # צילום טבלת תוכניות
            try:
                plans_container = page.locator("#table-taba")
                is_open = await plans_container.evaluate("el => el.classList.contains('in')")
                if not is_open:
                    tab_header = page.get_by_text("תוכניות למידע תכנוני").first
                    await tab_header.scroll_into_view_if_needed()
                    await tab_header.click(force=True)

                table_selector = "table.table-condensed:has-text('מספר תוכנית')"
                table_element = page.locator(table_selector).first
                await table_element.wait_for(state="visible", timeout=10000)
                await page.wait_for_timeout(1000)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                table_path = str(SCREENSHOT_DIR / f"{timestamp}_only_table.png")
                await table_element.screenshot(path=table_path)
            except Exception as e:
                print(f"שגיאה בצילום טבלת תוכניות: {e}")

            # צילום טבלת זכויות
            try:
                rights_container = page.locator("div:has(> table:has-text('זכות'))").first
                is_rights_open = await rights_container.is_visible()
                if not is_rights_open:
                    rights_tab = page.get_by_text("זכויות בתוקף לחלקה").first
                    await rights_tab.scroll_into_view_if_needed()
                    await rights_tab.click(force=True)

                rights_table = (
                    page.locator("table.table-condensed:has-text('זכות')").filter(visible=True).first
                )
                await rights_table.wait_for(state="visible", timeout=10000)
                await page.wait_for_timeout(1500)

                timestamp_rights = datetime.now().strftime("%Y%m%d_%H%M%S")
                rights_path = str(SCREENSHOT_DIR / f"{timestamp_rights}_rights_table.png")
                await rights_table.screenshot(path=rights_path)
            except Exception as e:
                print(f"שגיאה בצילום טבלת זכויות: {e}")

        except Exception as e:
            print(f"שגיאה במהלך ההרצה: {e}")
            await _take_screenshot(page, "ERROR_STATE", True)
            traceback.print_exc()
        finally:
            await browser.close()

        if table_path and rights_path:
            return table_path, rights_path
        print("❌ לא ניתן להחזיר תמונות - אחד או יותר מהצילומים נכשל.")
        return None, None


# -----------------------------
# 3) Orchestration: תמונות → טבלאות, ו-PDF להשלמה
# -----------------------------
async def fetch_taba_tables(
    *,
    city: str,
    gush: str,
    helka: str,
    base_path: str | Path,
    output_dir: Path,
) -> TabaTablesResult:
    """מחזיר 2 טבלאות מוכנות (תכניות + זכויות) ומסתיר את כל הלוגיקה בפנים."""
    base_path_str = str(base_path)
    plans_image_path: str | None = None
    rights_image_path: str | None = None

    plans_table: dict | None = None
    rights_table: dict | None = None
    rights_partial: dict | None = None

    # ניסיון ראשון: אתר הוועדה המקומית / מערכת הנדסה (תמונות)
    try:
        plans_image_path, rights_image_path = await run_scraper(
            city, gush, helka, base_path=base_path_str
        )
    except Exception as e:
        print(f"[report_steps.download_taba] שגיאה בהרצת run_scraper: {e}")
        plans_image_path, rights_image_path = None, None

    if plans_image_path and rights_image_path:
        # טבלת תכניות מתוך תמונה
        try:
            plans_table = _safe_table(
                await get_table_from_image(
                    image_path=plans_image_path,
                    extra_instructions=EXTRA_TABA_PLANS_INSTRUCTIONS,
                )
            )
        except Exception as e:
            print(f"[report_steps.download_taba] שגיאה בחילוץ טבלת תב\"ע מתמונה: {e}")

        # טבלת זכויות חלקית מתוך תמונה (להשלמה מול PDF)
        try:
            rights_partial = _safe_table(
                await get_table_from_image(
                    image_path=rights_image_path,
                    extra_instructions=EXTRA_PLANNING_RIGHTS_INSTRUCTIONS,
                )
            )
        except Exception as e:
            print(f"[report_steps.download_taba] שגיאה בחילוץ טבלת זכויות מתמונה: {e}")

    # הורדה ממרמ"י (PDF + אולי טבלת תכניות מהאתר) והשלמת זכויות
    pdf_files: list[Path] = []
    planning_table_from_rmi: dict | None = None
    try:
        taba_result = await download_taba_pdfs(gush=gush, helka=helka, output_dir=output_dir)
        pdf_files = taba_result.get("pdf_files", []) or []
        planning_table_from_rmi = _safe_table(taba_result.get("planning_table"))
        if plans_table is None and planning_table_from_rmi is not None:
            plans_table = planning_table_from_rmi
    except Exception as e:
        print(f"[report_steps.download_taba] שגיאה בהורדת תב\"ע ממרמ\"י: {e}")

    # זכויות: אם יש PDF - ננסה להוציא/להשלים טבלה מלאה; אחרת נסתפק בחלקית
    if pdf_files:
        try:
            rights_table = _safe_table(
                await generate_property_report(
                    [str(p) for p in pdf_files],
                    existing_rights_table=rights_partial,
                )
            )
        except Exception as e:
            print(f"[report_steps.download_taba] שגיאה בחילוץ זכויות מקבצי תב\"ע: {e}")
            rights_table = None

    if rights_table is None:
        rights_table = rights_partial

    return TabaTablesResult(
        plans_table=plans_table,
        rights_table=rights_table,
        plans_image_path=plans_image_path,
        rights_image_path=rights_image_path,
        pdf_files=pdf_files,
    )


async def fetch_taba_tables_only(
    *,
    city: str,
    gush: str,
    helka: str,
    base_path: str | Path,
    output_dir: Path,
) -> tuple[dict | None, dict | None]:
    res = await fetch_taba_tables(city=city, gush=gush, helka=helka, base_path=base_path, output_dir=output_dir)
    return res.plans_table, res.rights_table


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("שימוש:")
        print("python -m report_steps.download_taba <gush> <helka>")
        sys.exit(1)

    gush_arg = sys.argv[1]
    helka_arg = sys.argv[2]
    import asyncio

    asyncio.run(download_taba_pdfs(gush=gush_arg, helka=helka_arg, output_dir=DOWNLOAD_DIR))

