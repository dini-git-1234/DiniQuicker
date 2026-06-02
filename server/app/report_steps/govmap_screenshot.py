import asyncio
from pathlib import Path
from typing import Optional, Tuple

from playwright.async_api import async_playwright


async def capture_govmap(address: str, base_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    פותח את GOVMAP, מאתר את הגוש/חלקה ומצלם שתי תצוגות (מפה + צילום אויר).
    מחזיר (נתיב_צילום_מפה, נתיב_צילום_אויר) או (None, None) במקרה כשלון.
    """
    screenshot_dir = Path(base_path) / "screenshots" / "govmap"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    print("📁 Screenshot directory:", screenshot_dir.resolve())

    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        shot_paths: list[str] = []
        
        try:
            browser = await asyncio.wait_for(
                p.chromium.launch(headless=True),
                timeout=30
            )
            context = await asyncio.wait_for(
                browser.new_context(viewport={"width": 1920, "height": 1080}),
                timeout=15
            )
            page = await asyncio.wait_for(
                context.new_page(),
                timeout=15
            )
        
            # נריץ את אותה האוטומציה עבור שני קישורים שונים:
            base_urls = [
                "https://www.govmap.gov.il/?c=219143.61,618345.06&lay=217366,21,15",
                "https://www.govmap.gov.il/?c=206527.17,629388.64&lay=217366,21,15&z=6&b=1",
            ]
        
            for idx, base_url in enumerate(base_urls, start=1):
                try:
                    await asyncio.wait_for(
                        page.goto(
                            base_url,
                            wait_until="networkidle",
                            timeout=60000,
                        ),
                        timeout=70  # 70 seconds total timeout
                    )
                except asyncio.TimeoutError:
                    print(f"[govmap] TIMEOUT בעמוד {idx}, דילוג")
                    continue
                except Exception as e:
                    print(f"[govmap] שגיאה בעומס עמוד {idx}: {e}")
                    continue
            
                # המתנה לטעינה מלאה של הממשק
                await page.wait_for_timeout(4000)
            
                # ===== שימוש בשדה החיפוש הראשי =====
                search_input = page.locator("input[type='search'], input[placeholder*='חיפוש']").first
            
                # חיפוש לפי הכתובת שקיבלנו
                search_text = address
                try:
                    await asyncio.wait_for(search_input.click(), timeout=5)
                    await asyncio.wait_for(search_input.fill(search_text), timeout=5)
                    await page.wait_for_timeout(6000)
                    await asyncio.wait_for(search_input.press("Enter"), timeout=5)
                    await asyncio.wait_for(search_input.press("Enter"), timeout=5)
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"[govmap] שגיאה בחיפוש {idx}: {e}")
                    continue
            
                # המתנה לזום / טעינת התוצאה
                await page.wait_for_timeout(5000)
            
                # ===== צילום מסך רגיל =====
                map_shot_full = screenshot_dir / f"map_address_{idx}_full.png"
                try:
                    await asyncio.wait_for(
                        page.screenshot(path=str(map_shot_full)),
                        timeout=10
                    )
                    print(f"Saved: {map_shot_full}")
                except Exception as e:
                    print(f"[govmap] שגיאה בצילום מסך {idx}: {e}")
                    continue
            
                CROP_TOP_PERCENT = 0.12  # חיתוך מלמעלה (12%)
                CROP_LEFT_PERCENT = 0.06  # חיתוך משמאל (6%)
                CROP_RIGHT_PERCENT = 0.20  # חיתוך מימין (20%)
                CROP_BOTTOM_PERCENT = 0.08  # חיתוך מלמטה (8%)
            
                viewport = page.viewport_size
                width = viewport["width"]
                height = viewport["height"]
            
                clip = {
                    "x": int(width * CROP_LEFT_PERCENT),
                    "y": int(height * CROP_TOP_PERCENT),
                    "width": int(width * (1 - CROP_LEFT_PERCENT - CROP_RIGHT_PERCENT)),
                    "height": int(height * (1 - CROP_TOP_PERCENT - CROP_BOTTOM_PERCENT)),
                }
            
                map_shot_cropped = screenshot_dir / f"map_address_{idx}.png"
                try:
                    await asyncio.wait_for(
                        page.screenshot(path=str(map_shot_cropped), clip=clip),
                        timeout=10
                    )
                    print(f"Saved (cropped): {map_shot_cropped}")
                    shot_paths.append(str(map_shot_cropped))
                except Exception as e:
                    print(f"[govmap] שגיאה בצילום מסך cropped {idx}: {e}")
            
            # מחזירים את שני נתיבי הצילום: הראשון צילום מפה, השני צילום אויר
            if len(shot_paths) >= 2:
                return (shot_paths[0], shot_paths[1])
            if len(shot_paths) == 1:
                return (shot_paths[0], shot_paths[0])
            return (None, None)
        
        except Exception as e:
            print(f"[govmap] שגיאה חמורה ב-capture_govmap: {e}")
            return (None, None)
        finally:
            # ניקוי - הבטחה שה-browser יסגור בכל מקרה
            try:
                if page:
                    await asyncio.wait_for(page.close(), timeout=5)
            except Exception as e:
                print(f"[govmap] שגיאה בסגירת page: {e}")
            try:
                if context:
                    await asyncio.wait_for(context.close(), timeout=5)
            except Exception as e:
                print(f"[govmap] שגיאה בסגירת context: {e}")
            try:
                if browser:
                    await asyncio.wait_for(browser.close(), timeout=10)
            except Exception as e:
                print(f"[govmap] שגיאה בסגירת browser: {e}")


if __name__ == "__main__":
    import sys

    """
    הרצה ישירה של הכלי לצילום GOVMAP
    שימוש:
        python Govmap_screenshot.py "<כתובת לחיפוש>" "<בסיס נתיב לשמירה>"
    למשל:
        python Govmap_screenshot.py "רחוב הרצל 10 תל אביב" "c:/temp"
    אם לא הועברו ארגומנטים, משתמשים בערכי ברירת מחדל.
    """
    addr = sys.argv[1] if len(sys.argv) > 1 else "רחוב הרצל 10 תל אביב"
    base = sys.argv[2] if len(sys.argv) > 2 else "."

    shot1, shot2 = asyncio.run(capture_govmap(addr, base))
    print("צילום:", shot1)
    print("צילום אויר:", shot2)