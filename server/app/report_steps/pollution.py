from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright

from utils.temp_paths import temp_dir

import asyncio

async def check_soil_contamination(
    address: str,
    base_path: str | Path | None = None,
) -> Optional[str]:
    """
    בודק זיהום קרקע עבור כתובת.

    מחזיר:
    - None אם לא נמצא זיהום או במקרה של שגיאה
    - מחרוזת עם נתיב צילום מסך של טבלת הזיהום אם נמצא זיהום
    """
    async with async_playwright() as p:
        if base_path is None:
            screenshots_dir = temp_dir("screenshots", "pollution")
        else:
            screenshots_dir = Path(base_path) / "screenshots" / "pollution"
            screenshots_dir.mkdir(parents=True, exist_ok=True)

        # עדיף headless=True בסביבת שרת
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            print(f"ניגש לאתר עבור הכתובת: {address}")
            page = await context.new_page()

            await page.goto(
                "https://www.govmap.gov.il/?c=219143.61,618345.06",
                wait_until="networkidle",
                timeout=60000,
            )

            # המתנה לטעינה מלאה של הממשק
            await page.wait_for_timeout(4000)

            # ===== חיפוש גוש / חלקה =====
            search_text = address

            # שדה החיפוש הראשי (בד"כ input עם role=searchbox)
            search_input = page.locator(
                "input[type='search'], input[placeholder*='חיפוש']"
            ).first
            await search_input.click()
            await search_input.fill(search_text)
            await page.wait_for_timeout(6000)
            await search_input.press("Enter")
            await search_input.press("Enter")

            # המתנה לזום / טעינת התוצאה
            await page.wait_for_timeout(5000)

            # ===== 2. הפעלת שכבת "קרקעות מזוהמות" =====
            try:
                print("מנסה לפתוח את פאנל השכבות...")

                layers_btn_selector = "div._layersBtn_mh6nk_89"
                layers_btn = page.locator(layers_btn_selector)
                await layers_btn.wait_for(state="visible", timeout=10000)
                await layers_btn.click()

                print("פאנל שכבות נפתח. מחפש את השכבה...")
                await page.wait_for_timeout(2000)

                layer_input_selector = "input._withStartIcon_vug93_25"
                layer_search = page.locator(layer_input_selector)
                await page.screenshot(path=str(screenshots_dir / "layers1.png"))

                await layer_search.wait_for(state="visible", timeout=5000)
                await layer_search.fill("קרקעות מזוהמות")
                await page.wait_for_timeout(2000)

                contamination_result = page.get_by_text("קרקעות מזוהמות", exact=False).last
                await contamination_result.click()
                await page.screenshot(path=str(screenshots_dir / "layers2.png"))

                print("✅ שכבת 'קרקעות מזוהמות' הופעלה")
                await page.wait_for_timeout(4000)

                print("📦 פותח יישומים...")
                applications_btn = page.locator("div._applicationsBtn_mh6nk_93")
                await applications_btn.wait_for(state="visible")
                await applications_btn.click()
                await page.wait_for_timeout(1000)

                print("🔍 בוחר ניתוח מרחבי...")
                spatial_analysis_card = page.locator(
                    "div._cardContainer_1pqiy_1", has_text="ניתוח מרחבי"
                )
                await spatial_analysis_card.click()
                await page.wait_for_timeout(2000)

                print("🚀 לוחץ על בצע ניתוח מרחבי...")
                run_analysis_btn = page.locator(
                    "button", has_text="בצע ניתוח מרחבי לשכבה שנבחרה"
                )
                await run_analysis_btn.click()
                await page.wait_for_timeout(1000)

                print("⭕ בוחר סימון לפי עיגול...")
                circle_btn = page.locator(
                    "button._cardButton_1cwwf_225", has_text="סימון לפי עיגול"
                )
                await circle_btn.click()

                await page.mouse.click(1920 / 2, 1080 / 2)
                await page.wait_for_timeout(2000)

                print("📊 מציג תוצאות...")
                show_results_btn = page.locator("button", has_text="הצג תוצאות")
                await show_results_btn.click()

                await page.wait_for_timeout(5000)

                final_path = screenshots_dir / "spatial_analysis_result.png"
                await page.screenshot(path=str(final_path), full_page=False)
                print(f"✅ תהליך הושלם! צילום נשמר ב: {final_path}")

                print("⏳ בודק האם קיימות תוצאות זיהום...")
                results_panel_selector = ".MuiDataGrid-main"

                try:
                    results_panel = page.locator(results_panel_selector)
                    await results_panel.wait_for(state="visible", timeout=7000)
                    await page.set_viewport_size({"width": 3500, "height": 1200})
                    await page.wait_for_timeout(2000)
                    print("🚨 נמצא זיהום! מצלם את טבלת הנתונים...")

                    final_table_path = screenshots_dir / "pollution_results_table.png"
                    await results_panel.screenshot(path=str(final_table_path))

                    print(f"✅ טבלת הזיהום נשמרה ב: {final_table_path}")
                    return str(final_table_path)

                except Exception:
                    print("✅ לא נמצאו תוצאות - הקרקע לא מזוהמת.")
                    return None

            except Exception as e:
                print(f"❌ שגיאה בתהליך: {e}")

        except Exception as e:
            print(f"אירעה שגיאה: {e}")
            await page.screenshot(path=str(screenshots_dir / "error.png"))

        finally:
            await browser.close()
            print("התהליך הסתיים. הצילומים שמורים בתיקיית screenshots.")

    return None

