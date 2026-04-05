# 📰 NYT Article Scraper (Hybrid: Requests + Playwright)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" />
  <img src="https://img.shields.io/badge/Playwright-Automation-green.svg" />
  <img src="https://img.shields.io/badge/Status-Active-success.svg" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
</p>

---

## 🚀 Overview

A robust Python-based scraper for extracting structured data from New York Times articles.

Built with a **hybrid scraping strategy**:

* ⚡ Fast HTTP requests (Requests)
* 🤖 Browser automation fallback (Playwright)

Designed to handle **modern JS-heavy websites and anti-bot protections**.

---

## ✨ Features

* 📄 Extract:

  * Title
  * Author (Byline)
  * Published Date
  * Updated Date
  * Article Content

* 🧠 Multi-layer parsing:

  * JSON-LD (primary)
  * Next.js (`__NEXT_DATA__`)
  * HTML fallback
  * Meta tags fallback

* 🔄 Smart fallback system:

  * Requests → Playwright

* 🧹 Data cleaning:

  * Removes duplicates
  * Normalizes whitespace
  * Formats ISO dates

---

## 🛠️ Tech Stack

* Python
* BeautifulSoup
* Requests
* Playwright
* Dataclasses

---

## 📦 Installation

```bash
git clone https://github.com/qayam-shaikh/web-scraper.git
cd web-scraper
pip install -r requirements.txt
playwright install
```

---

## ▶️ Usage

```bash
python scraper.py "https://www.nytimes.com/..."
```

---

## 📸 Example Output

```text
Title: Iran’s Military Strength Is Being Tested
Byline: John Doe
Published: 2026-04-03T10:00:00+00:00
Updated: 2026-04-03T12:00:00+00:00

--------------------------------------------------------------------------------

Iranian operatives have been digging out underground missile bunkers...
```

---

## 🧠 Architecture

```text
            ┌───────────────┐
            │   Fetch HTML  │
            └──────┬────────┘
                   │
        ┌──────────▼──────────┐
        │   Requests (fast)   │
        └──────────┬──────────┘
                   │ fallback
        ┌──────────▼──────────┐
        │   Playwright (JS)   │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │   JSON-LD Parsing   │
        ├──────────┬──────────┤
        │ __NEXT_DATA__       │
        │ HTML Parsing        │
        │ Meta Tags           │
        └─────────────────────┘
```

---

## ⚠️ Limitations

* 🚫 Some content may be partially inaccessible due to:

  * Paywalls
  * CAPTCHA / bot detection
  * Protected APIs

* Playwright improves reliability but does not guarantee full extraction.

---

## 🔀 Branches

* `main` and `hybrid-scraper` → Hybrid (Requests + Playwright)
* `browserAutomation` → Playwright-only


---

## 🔮 Future Improvements

* 🔌 API-based scraping (GraphQL)
* 🌐 Multi-site support
* 💾 Export to JSON/CSV
* ⚙️ Advanced CLI options

---

## 🧪 Sample Test URL

```text
https://www.nytimes.com/...
```

---

## 📄 License

MIT License

---

## 👨‍💻 Author

**Qayaam Shaikh**

---

## ⭐ Show your support

If you found this useful, give it a ⭐ on GitHub!
