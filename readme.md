# 📟 Nook Energy Dashboard (Home Assistant + Android 2.1)

A lightweight energy dashboard designed to run on a **Barnes & Noble Nook e-ink display**, powered by Home Assistant.

---

## 🧾 Overview

Old Nook e-readers are surprisingly perfect for always-on dashboards:

- 🪶 Ultra low power (e-ink screen)
- 📐 600 × 800 resolution
- 💷 Easily found on eBay for **~£15**
- 📱 Runs **Android 2.1 (API 7)**

This project turns one into a **real-time Home Assistant energy display**.

---

## 🔓 Rooting the Nook

To get this working, you’ll need to root the device.

The easiest way is:

- Search for **“NookManager”**
- Flash it to an SD card
- Boot the device from the card

That gives you access to install your own APKs and run custom apps.

*(Plenty of guides online – no need to reinvent the wheel here)*

---

## 🏠 Home Assistant Integration

The dashboard pulls data directly from **Home Assistant** via:

```
/api/states
```

- Uses a **long-lived access token**
- Fetches all entity states
- Maps them to UI elements

This means you can display anything:

- Solar production
- Battery state
- Grid import/export
- Costs (e.g. Octopus)
- Temperature, EV charge, etc.

My current integrations
- Ocotpus Energy
- Sunsynk Solar Inverter
- Google Nest Thermostat
- Tesla Model Y

---

## 🎨 Dashboard Designer

The layout is created using:

👉 `dashboard_designer.py`

Run it locally:

```bash
python dashboard_designer.py
```

### Features

- Drag & drop Home Assistant entities
- 600 × 800 canvas (matches Nook screen exactly)
- Add:
  - Text
  - Lines
  - Boxes
  - Images
- Resize and position elements visually
- Export as a **self-contained HTML dashboard**

### Why this matters

Designing directly for e-ink is painful otherwise.  
This gives you **pixel-perfect control** before deploying to the device.

---

## 📱 Android App

The Nook runs a simple Android app:

👉 `MainActivity.java`

### How it works

- Loads exported `dashboard.html` from assets
- Uses a **WebView** (Android 2.1 compatible)
- Polls Home Assistant every **30 seconds**
- Updates values using Java → JS injection

### ⚡ E-ink optimisation

E-ink screens hate full refreshes (ghosting + flashing), so:

- Entities are split into **update groups**
- Each group updates with a delay (e.g. 5 seconds)
- Prevents full screen redraws
- Keeps the display stable and readable

```java
private static final long REFRESH_INTERVAL = 30000;
private static final long GROUP_DELAY = 5000;
```

This is the key trick that makes it usable on old hardware.

---

## 🖼 Screenshots

### 🧰 Designer UI

![Designer Screen](designerScreen.png)

### 📟 Nook Display

![Nook Screen](nookScreen.png)

---

## 🚀 Workflow

1. **Design dashboard**
   ```bash
   python dashboard_designer.py
   ```

2. **Export HTML**

3. Copy to Android project:
   ```
   app/src/main/assets/dashboard.html
   ```

4. Build & install APK on Nook

5. Done 🎉

---

## 💡 Why this project exists

Modern tablets are:

- Too bright
- Power hungry
- Overkill

The Nook is:

- Always-on
- Silent
- Minimal
- Cheap

Perfect for a **wall-mounted energy dashboard**.

---

## 🔧 Future Ideas

- Touch input / navigation
- Auto brightness / night mode
- OTA dashboard updates
- Better caching of HA responses

---

## 🧠 Notes

- Android 2.1 is *very* limited (no modern JS features)
- Keep HTML simple
- Avoid heavy animations (e-ink won’t like it)
- Base64 images are used so everything works offline
