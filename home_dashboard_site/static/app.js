"use strict";

// ==================================================
// 時計と日付を更新
// ==================================================

function updateClock() {
  const now = new Date();
  const clock = document.getElementById("clock");

  if (clock) {
    clock.textContent = new Intl.DateTimeFormat("ja-JP", {
      timeZone: "Asia/Tokyo",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    }).format(now);
  }

  const date = document.getElementById("clockDate");

  if (date) {
    const dateText = new Intl.DateTimeFormat("ja-JP", {
      timeZone: "Asia/Tokyo",
      year: "numeric",
      month: "long",
      day: "numeric"
    }).format(now);

    const weekday = new Intl.DateTimeFormat("ja-JP", {
      timeZone: "Asia/Tokyo",
      weekday: "short"
    }).format(now);

    date.textContent = `${dateText}(${weekday})`;
  }
}

updateClock();
setInterval(updateClock, 1000);


// ==================================================
// 外観設定（ライト・ダーク・端末設定）
// ==================================================

const themeToggle = document.getElementById("themeToggle");
const appearanceSetting = document.body.dataset.appearance || "system";

function devicePrefersDark() {
  return window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function getCurrentTheme() {
  return document.body.classList.contains("dark") ? "dark" : "light";
}

// ==================================================
// 下部メニューの選択状態とアイコン画像
// ==================================================

function getActiveBottomNavKey() {
  const path = window.location.pathname;
  const hash = window.location.hash;

  // ホーム
  if (path === "/") {
    return "home";
  }

  // 運行情報・時刻表
  if (
    path === "/operation" ||
    path.startsWith("/operation/")
  ) {
    return "operation";
  }

  // カレンダー
  if (
    path === "/calendar" ||
    path.startsWith("/calendar/") ||
    hash === "#events"
  ) {
    return "calendar";
  }

  // 時間割
  if (
    path === "/schedule" ||
    path.startsWith("/schedule/")
  ) {
    return "schedule";
  }

  // その他
  if (
    path === "/more" ||
    path.startsWith("/more/") ||
    hash === "#weather"
  ) {
    return "more";
  }

  return null;
}


function updateBottomNavIcons(theme = getCurrentTheme()) {
  const activeKey = getActiveBottomNavKey();

  const fileNames = {
    home: "home.png",
    operation: "operation.png",
    calendar: "calendar.png",
    schedule: "schedule.png",
    more: "more.png"
  };

  document.querySelectorAll(".bottom-nav .nav-item").forEach((item) => {
    const img = item.querySelector(".nav-icon");
    if (!img) return;

    const key = item.dataset.navKey;
    const fileName = fileNames[key];

    if (!fileName) return;

    const isActive = key === activeKey;

    // 選択中は active、それ以外はライト・ダーク別の画像
    const imagePath = isActive
      ? `/static/icons/active/${fileName}`
      : `/static/icons/${theme}/${fileName}`;

    // 同じ画像への再設定を避ける
    if (img.dataset.currentIconPath !== imagePath) {
      img.dataset.currentIconPath = imagePath;

      img.onerror = function () {
        console.error("下部メニューのアイコンを読み込めません:", imagePath);
        img.onerror = null;

        // 選択中の画像がない場合は、現在のテーマ用画像を試す
        if (isActive) {
          const fallbackPath = `/static/icons/${theme}/${fileName}`;
          img.dataset.currentIconPath = fallbackPath;
          img.src = fallbackPath;
        }
      };

      img.src = imagePath;
    }

    item.classList.toggle("active", isActive);

    if (isActive) {
      item.setAttribute("aria-current", "page");
    } else {
      item.removeAttribute("aria-current");
    }
  });
}

// ==================================================
// 通常アイコンをライト・ダーク別の画像に切り替える
// ==================================================

function updateThemeIcons(theme) {
  // 下部メニューは専用関数で処理する
  document.querySelectorAll(
    "img.custom-icon:not(.nav-icon)"
  ).forEach((img) => {
    const currentSrc =
      img.dataset.baseSrc || img.getAttribute("src") || "";

    if (!img.dataset.baseSrc) {
      img.dataset.baseSrc = currentSrc;
    }

    const fileName =
      img.dataset.iconName || img.dataset.baseSrc.split("/").pop();

    img.dataset.iconName = fileName;

    const themedSrc = `/static/icons/${theme}/${fileName}`;

    img.onerror = function () {
      img.onerror = null;
      img.src = img.dataset.baseSrc;
    };

    img.src = themedSrc;
  });

  updateBottomNavIcons(theme);
}


// ==================================================
// 天気アイコン
// ==================================================

let currentWeather = null;


function updateWeatherIcon(weather) {
  const symbol = document.getElementById("weatherSymbol");

  if (!symbol || !weather) return;

  const theme = getCurrentTheme();

  const imagePath =
    `/static/icons/weather/${theme}/${weather.image}`;

  symbol.innerHTML = "";
  symbol.classList.remove("weather-icon-error");

  const img = document.createElement("img");

  img.alt = weather.label;
  img.className = "weather-condition-icon";

  img.onerror = function () {
    console.error(
      "天気アイコンの読み込みに失敗しました:",
      imagePath
    );

    img.onerror = null;
    symbol.innerHTML = "";
    symbol.classList.add("weather-icon-error");
  };

  img.src = imagePath;
  symbol.appendChild(img);
}


// ==================================================
// ライト・ダークモードの反映
// ==================================================

function setTheme(theme) {
  const normalizedTheme = theme === "dark" ? "dark" : "light";

  document.body.classList.toggle(
    "dark",
    normalizedTheme === "dark"
  );

  document.documentElement.dataset.theme = normalizedTheme;

  // 通常アイコンと下部メニューを更新
  updateThemeIcons(normalizedTheme);

  // テーマ切り替えボタンのアイコン
  const themeIcon = document.getElementById("themeIcon");

  if (themeIcon) {
    themeIcon.onerror = null;

    themeIcon.src = normalizedTheme === "dark"
      ? "/static/icons/theme-light.png"
      : "/static/icons/theme-dark.png";
  }

  // 天気アイコンもテーマに合わせて更新
  if (currentWeather) {
    updateWeatherIcon(currentWeather);
  }
}


// 初期テーマを決定
const savedTheme = localStorage.getItem("myHomeTheme");

const initialTheme = savedTheme ||
  (
    appearanceSetting === "system"
      ? (devicePrefersDark() ? "dark" : "light")
      : appearanceSetting
  );

setTheme(initialTheme);


// テーマ切り替えボタン
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const nextTheme = getCurrentTheme() === "dark"
      ? "light"
      : "dark";

    localStorage.setItem("myHomeTheme", nextTheme);

    setTheme(nextTheme);
  });
}


// 端末の外観設定変更を監視
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)")
    .addEventListener?.("change", () => {
      if (
        !localStorage.getItem("myHomeTheme") &&
        appearanceSetting === "system"
      ) {
        setTheme(devicePrefersDark() ? "dark" : "light");
      }
    });
}


// ==================================================
// 下部メニューの移動・選択状態を更新
// ==================================================

document.querySelectorAll(".bottom-nav .nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    const href = item.getAttribute("href") || "";

    if (href.endsWith("#events") || href.endsWith("#weather")) {
      const key = href.endsWith("#events") ? "events" : "weather";

      // クリックしたセクションを選択状態にする
      document.querySelectorAll(".bottom-nav .nav-item").forEach((navItem) => {
        if (navItem.dataset.navKey === key) {
          navItem.classList.add("active");
        } else {
          navItem.classList.remove("active");
        }
      });

      updateBottomNavIcons();
    }
  });
});


// URLのハッシュが変更された場合も更新
window.addEventListener("hashchange", () => {
  updateBottomNavIcons();
});


// ブラウザの戻る・進むでも選択状態を更新
window.addEventListener("pageshow", () => {
  updateBottomNavIcons();
});


// ==================================================
// 運行情報（1分ごとに更新）
// ==================================================

const operationTopLink =
  document.getElementById("operationTopLink");

const operationStatusText =
  document.getElementById("operationStatusText");

const operationTopLabel =
  document.querySelector(".operation-top-label");


async function loadOperationStatus() {
  if (!operationStatusText) return;

  try {
    const response = await fetch("/api/operation", {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error("operation request failed");
    }

    const data = await response.json();

    if (operationTopLabel && data.route) {
      operationTopLabel.textContent = data.route;
    }

    operationStatusText.textContent =
      data.status || "取得できません";

    operationStatusText.dataset.state = data.ok
      ? (data.status === "平常運転" ? "normal" : "alert")
      : "error";

    if (operationTopLink) {
      operationTopLink.href =
        data.source_url ||
        "https://transit.yahoo.co.jp/diainfo/area/4";

      operationTopLink.title =
        `${data.route || "運行情報"}：` +
        `${data.status || "取得できません"}。` +
        `${data.detail || ""}`;

      operationTopLink.setAttribute(
        "aria-label",
        operationTopLink.title
      );
    }
  } catch (error) {
    console.error("運行情報の取得に失敗しました:", error);

    operationStatusText.textContent = "取得できません";
    operationStatusText.dataset.state = "error";

    if (operationTopLink) {
      operationTopLink.title =
        "運行情報を取得できません。時間をおいて再読み込みしてください。";
    }
  }
}

if (operationStatusText) {
  loadOperationStatus();
  setInterval(loadOperationStatus, 60 * 1000);
}


// ==================================================
// 天気の地点設定
// ==================================================

const WEATHER_PLACES = {
  utsunomiya: {
    label: "宇都宮市",
    lat: 36.5551,
    lon: 139.8828
  },

  oyama: {
    label: "小山市",
    lat: 36.3147,
    lon: 139.8002
  },

  tochigi: {
    label: "栃木市",
    lat: 36.3824,
    lon: 139.7342
  },

  sano: {
    label: "佐野市",
    lat: 36.3145,
    lon: 139.5783
  },

  ashikaga: {
    label: "足利市",
    lat: 36.3402,
    lon: 139.4497
  }
};


// ==================================================
// 天気コードと画像の対応
// ==================================================

function describeWeather(code) {
  if (code === 0) {
    return {
      label: "快晴",
      image: "clear.png",
      fallback: "☀"
    };
  }

  if ([1, 2].includes(code)) {
    return {
      label: "晴れ・一部くもり",
      image: "partly-cloudy.png",
      fallback: "🌤"
    };
  }

  if (code === 3) {
    return {
      label: "くもり",
      image: "cloudy.png",
      fallback: "☁"
    };
  }

  if ([45, 48].includes(code)) {
    return {
      label: "霧",
      image: "fog.png",
      fallback: "🌫"
    };
  }

  if ([51, 53, 55, 56, 57].includes(code)) {
    return {
      label: "霧雨",
      image: "drizzle.png",
      fallback: "🌦"
    };
  }

  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) {
    return {
      label: "雨",
      image: "rain.png",
      fallback: "🌧"
    };
  }

  if ([71, 73, 75, 77, 85, 86].includes(code)) {
    return {
      label: "雪",
      image: "snow.png",
      fallback: "❄"
    };
  }

  if ([95, 96, 99].includes(code)) {
    return {
      label: "雷雨",
      image: "thunderstorm.png",
      fallback: "⛈"
    };
  }

  return {
    label: "天気",
    image: "default.png",
    fallback: "🌡"
  };
}


// ==================================================
// 選択した地点の天気予報を取得
// ==================================================

async function loadWeather() {
  const key = document.body.dataset.weatherPlace || "sano";
  const place = WEATHER_PLACES[key] || WEATHER_PLACES.sano;

  const url =
    `https://api.open-meteo.com/v1/forecast` +
    `?latitude=${place.lat}` +
    `&longitude=${place.lon}` +
    `&current=temperature_2m,weather_code` +
    `&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max` +
    `&timezone=Asia%2FTokyo` +
    `&forecast_days=1`;

  const location = document.getElementById("weatherLocation");

  if (location) {
    location.textContent = place.label;
  }

  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error("weather request failed");
    }

    const data = await response.json();

    const current = data.current;
    const daily = data.daily;

    const weather = describeWeather(current.weather_code);

    currentWeather = weather;

    const temperature = document.getElementById("weatherTemp");
    const description = document.getElementById("weatherDesc");
    const maximum = document.getElementById("weatherMax");
    const minimum = document.getElementById("weatherMin");
    const rain = document.getElementById("weatherRain");

    if (temperature) {
      temperature.textContent =
        `${Math.round(current.temperature_2m)}°`;
    }

    if (description) {
      description.textContent = weather.label;
    }

    updateWeatherIcon(weather);

    if (maximum) {
      maximum.textContent =
        `${Math.round(daily.temperature_2m_max[0])}°`;
    }

    if (minimum) {
      minimum.textContent =
        `${Math.round(daily.temperature_2m_min[0])}°`;
    }

    if (rain) {
      rain.textContent =
        `${daily.precipitation_probability_max?.[0] ?? "--"}%`;
    }
  } catch (error) {
    console.error("天気情報の取得に失敗しました:", error);

    const description = document.getElementById("weatherDesc");

    if (description) {
      description.textContent = "天気情報を取得できません";
    }
  }
}


// ==================================================
// 初期表示
// ==================================================

// ページを開いたときに下部メニューの画像を設定
updateBottomNavIcons();


// 天気表示があるページだけで取得
if (document.getElementById("weatherTemp")) {
  loadWeather();
}