import asyncio
import os
import time

import googlemaps
from playwright.async_api import async_playwright  # שינוי ל-async_api


API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("[comparable_sales] WARNING: GOOGLE_API_KEY is not set; Google Maps geocoding will be skipped.")


# הגדרת הפונקציה כאסינכרונית
async def run_nadlan_search(address, property_type, base_path):
    folder_name = f"search_{address.replace(' ', '_').replace(',', '')}_{int(time.time())}"
    full_output_dir = os.path.join(base_path, "screenshots", "nadlan", folder_name)
    os.makedirs(full_output_dir, exist_ok=True)

    table_screenshot_path = os.path.join(full_output_dir, "final_table_results.png")

    async with async_playwright() as p:  # שימוש ב-async with
        # קבלת neighborhood עם timeout
        try:
            neighborhood = await asyncio.wait_for(
                asyncio.to_thread(get_neighborhood, address),
                timeout=15  # 15 seconds timeout for Google Maps API
            )
        except asyncio.TimeoutError:
            print(f"[nadlan] TIMEOUT בקבלת neighborhood מ-Google Maps")
            neighborhood = address
        except Exception as e:
            print(f"[nadlan] שגיאה בקבלת neighborhood: {e}")
            neighborhood = address

        print(f"הכתובת: {address} {neighborhood}")
        # headless=True בדוקר/שרת (אין תצוגה); להצגת דפדפן מקומית: PLAYWRIGHT_HEADED=1
        headless = os.environ.get("PLAYWRIGHT_HEADED", "").strip().lower() not in (
            "1",
            "true",
            "yes",
        )
        
        browser = None
        context = None
        page = None
        
        try:
            browser = await asyncio.wait_for(
                p.chromium.launch(headless=headless),
                timeout=30
            )
            context = await asyncio.wait_for(
                browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ),
                timeout=15
            )

            # קוד שמסתיר את העובדה שזה אוטומציה (מוחק את ה-flag של webdriver)
            await asyncio.wait_for(
                context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                ),
                timeout=10
            )
            page = await asyncio.wait_for(
                context.new_page(),
                timeout=15
            )

            try:
                print(f"ניגש לאתר עבור כתובת: {address}...")
                await asyncio.wait_for(
                    page.goto("https://www.nadlan.gov.il/", wait_until="networkidle"),
                    timeout=70
                )
            except asyncio.TimeoutError:
                print(f"[nadlan] TIMEOUT בטעינת nadlan.gov.il")
                return None
            except Exception as e:
                print(f"[nadlan] שגיאה בטעינת nadlan.gov.il: {e}")
                return None

            await page.screenshot(path=os.path.join(full_output_dir, "01_homepage.png"))

            search_input = page.locator("#myInput2")
            await asyncio.wait_for(search_input.fill(neighborhood), timeout=5)
            await asyncio.sleep(1)  # שימוש ב-asyncio.sleep במקום time.sleep
            await asyncio.wait_for(search_input.press("Enter"), timeout=5)

            await page.wait_for_timeout(4000)
            await page.screenshot(path=os.path.join(full_output_dir, "02_after_search.png"))

            print("מגדיר פילטרים...")
            await asyncio.wait_for(page.locator("button.filterBtn:has-text('סינון')").click(), timeout=5)
            await page.wait_for_timeout(1000)

            # סוג נכס
            await asyncio.wait_for(page.get_by_role("button", name="כל סוגי הנכסים").click(), timeout=5)
            await asyncio.wait_for(page.get_by_role("button", name=property_type, exact=True).click(), timeout=5)

            # סגירה והחלה
            await asyncio.wait_for(page.locator("button.filterBtn.active").click(), timeout=5)

            print("מבצע מיון לפי תאריך...")
            # לחיצה על כפתור "מיון" (שימוש ב-filterBtn וטקסט)
            await asyncio.wait_for(page.locator("button.filterBtn:has-text('מיון')").click(), timeout=5)
            await page.wait_for_timeout(1000)  # המתנה קלה לפתיחת התפריט

            # לחיצה על האופציה "תאריך עסקה - סדר יורד"
            await asyncio.wait_for(page.get_by_role("button", name="תאריך עסקה - סדר יורד").click(), timeout=5)
            await page.wait_for_timeout(2000)  # המתנה לעדכון המיון

            # לחיצה חוזרת על כפתור המיון לסגירה (אם נדרש)
            await asyncio.wait_for(page.locator("button.filterBtn:has-text('מיון')").click(), timeout=5)

            print("המיון הושלם בהצלחה.")

            print("ממתין לעדכון הטבלה...")
            await page.wait_for_timeout(5000)

            table_locator = page.locator("#dealsTable")

            if await table_locator.is_visible():
                await table_locator.scroll_into_view_if_needed()
                await asyncio.wait_for(
                    table_locator.screenshot(path=table_screenshot_path),
                    timeout=10
                )
                print(f"צילום הטבלה נשמר ב: {table_screenshot_path}")
            else:
                print("הטבלה לא נמצאה.")
                table_screenshot_path = None

            await page.screenshot(
                path=os.path.join(full_output_dir, "06_final_results_full_page.png")
            )
            return table_screenshot_path

        except asyncio.TimeoutError:
            print(f"[nadlan] TIMEOUT בניתוח Playwright")
            return None
        except Exception as e:
            print(f"[nadlan] אירעה שגיאה: {e}")
            try:
                error_path = os.path.join(full_output_dir, "error_state.png")
                if page:
                    await asyncio.wait_for(
                        page.screenshot(path=error_path),
                        timeout=5
                    )
            except:
                pass
            return None

        finally:
            # ניקוי - הבטחה שכל המשאבים יסגורו
            try:
                if page:
                    await asyncio.wait_for(page.close(), timeout=5)
            except Exception as e:
                print(f"[nadlan] שגיאה בסגירת page: {e}")
            try:
                if context:
                    await asyncio.wait_for(context.close(), timeout=5)
            except Exception as e:
                print(f"[nadlan] שגיאה בסגירת context: {e}")
            try:
                if browser:
                    await asyncio.wait_for(browser.close(), timeout=10)
            except Exception as e:
                print(f"[nadlan] שגיאה בסגירת browser: {e}")


def get_neighborhood(address):
    if not API_KEY:
        print("[get_neighborhood] GOOGLE_API_KEY missing; skipping geocode.")
        return address

    # חיבור לשירות של גוגל
    gmaps = googlemaps.Client(key=API_KEY)

    # ביצוע Geocoding לכתובת
    # נגדיר language='he' כדי לקבל תוצאות בעברית
    try:
        geocode_result = gmaps.geocode(address, language="he")
    except Exception as e:
        print(f"[get_neighborhood] שגיאה ב-Google Maps API: {e}")
        return address

    if not geocode_result:
        return address

    # מעבר על כל מרכיבי הכתובת שחזרו מגוגל
    address_components = geocode_result[0]["address_components"]

    neighborhood = None
    sublocality = None

    for component in address_components:
        types = component["types"]

        # גוגל משתמשת בכמה תגיות לשכונות, נבדוק את הנפוצות שבהן
        if "neighborhood" in types:
            neighborhood = component["long_name"]
        if "sublocality_level_1" in types:
            sublocality = component["long_name"]

    # עדיפות ראשונה ל'neighborhood', אם אין - נחזיר את ה'sublocality'
    return neighborhood or sublocality or address


if __name__ == "__main__":
    my_base_path = "./my_nadlan_data"
    asyncio.run(run_nadlan_search("טבנקין ירושלים", "דירה", my_base_path))
