import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.10/firebase-app.js";
import { getFirestore, doc, getDoc, setDoc, updateDoc, increment, collection, getDocs } from "https://www.gstatic.com/firebasejs/9.6.10/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyCMUf4-ODAegkRC1RMfzbuYGTtA6r_9gSY",
  authDomain: "py-page.firebaseapp.com",
  projectId: "py-page",
  storageBucket: "py-page.appspot.com",
  messagingSenderId: "1028528276815",
  appId: "1:1028528276815:web:ea15a014fa245f1e2e713a",
  measurementId: "G-8TBQEL76YE"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// 獲取訪客的國家資訊
async function getVisitorCountry() {
    try {
        const response = await fetch('https://ipapi.co/json/');
        const data = await response.json();
        return data.country_name || "Unknown"; // 如果獲取失敗，回傳 "Unknown"
    } catch (error) {
        console.error('Error fetching country:', error);
        return "Unknown";
    }
}

// 獲取訪客的 IP 地址
async function getVisitorIP() {
    try {
        const response = await fetch('https://ipapi.co/json/');
        const data = await response.json();
        return data.ip || "Unknown"; // 如果獲取失敗，回傳 "Unknown"
    } catch (error) {
        console.error('Error fetching IP:', error);
        return "Unknown";
    }
}

// 更新各國瀏覽數量
async function updateVisitorCount() {
    const country = await getVisitorCountry();
    const ip = await getVisitorIP();
    const visitorRef = doc(db, "visitors", country);
    const ipRef = doc(db, "ips", ip);

    try {
        const ipSnap = await getDoc(ipRef);
        const now = new Date();
        const lastVisitTime = ipSnap.exists() ? ipSnap.data().lastVisitTime.toDate() : null;

        // 檢查是否在過去 30 分鐘內訪問過
        if (!lastVisitTime || (now - lastVisitTime) > 30 * 60 * 1000) {
            const visitorSnap = await getDoc(visitorRef);
            if (visitorSnap.exists()) {
                await updateDoc(visitorRef, { count: increment(1) });
            } else {
                await setDoc(visitorRef, { count: 1 });
            }

            // 更新 IP 的最後訪問時間
            await setDoc(ipRef, { lastVisitTime: now });

            // 讀取所有國家的計數
            const snapshot = await getDoc(visitorRef);
            const data = snapshot.data();

            // 顯示統計數據
            displayVisitorCounts(country, data.count);
        }
    } catch (error) {
        console.error("Error updating visitor count:", error);
    }
}

// 將國家名稱轉換為 ISO 代碼
function getCountryCode(countryName) {
    const countryCodes = {
        "Afghanistan": "af", "Albania": "al", "Algeria": "dz", "Andorra": "ad", "Angola": "ao", "Argentina": "ar",
        "Australia": "au", "Austria": "at", "Azerbaijan": "az", "Bahamas": "bs", "Bahrain": "bh", "Bangladesh": "bd",
        "Barbados": "bb", "Belarus": "by", "Belgium": "be", "Belize": "bz", "Benin": "bj", "Bhutan": "bt", "Bolivia": "bo",
        "Bosnia and Herzegovina": "ba", "Botswana": "bw", "Brazil": "br", "Brunei": "bn", "Bulgaria": "bg", "Burkina Faso": "bf",
        "Burundi": "bi", "Canada": "ca", "Chile": "cl", "China": "cn", "Colombia": "co", "Costa Rica": "cr", "Croatia": "hr",
        "Cuba": "cu", "Cyprus": "cy", "Czechia": "cz", "Denmark": "dk", "Dominican Republic": "do", "Ecuador": "ec",
        "Egypt": "eg", "El Salvador": "sv", "Estonia": "ee", "Finland": "fi", "France": "fr", "Germany": "de",
        "Greece": "gr", "Guatemala": "gt", "Haiti": "ht", "Honduras": "hn", "Hungary": "hu", "Iceland": "is", "India": "in",
        "Indonesia": "id", "Iran": "ir", "Iraq": "iq", "Ireland": "ie", "Israel": "il", "Italy": "it", "Jamaica": "jm",
        "Japan": "jp", "Jordan": "jo", "Kazakhstan": "kz", "Kenya": "ke", "Kuwait": "kw", "Latvia": "lv", "Lebanon": "lb",
        "Libya": "ly", "Lithuania": "lt", "Luxembourg": "lu", "Malaysia": "my", "Maldives": "mv", "Mexico": "mx",
        "Monaco": "mc", "Mongolia": "mn", "Morocco": "ma", "Nepal": "np", "Netherlands": "nl", "New Zealand": "nz",
        "Nigeria": "ng", "Norway": "no", "Oman": "om", "Pakistan": "pk", "Palestine": "ps", "Panama": "pa", "Peru": "pe",
        "Philippines": "ph", "Poland": "pl", "Portugal": "pt", "Qatar": "qa", "Romania": "ro", "Russia": "ru", "Saudi Arabia": "sa",
        "Senegal": "sn", "Serbia": "rs", "Singapore": "sg", "Slovakia": "sk", "Slovenia": "si", "South Africa": "za",
        "South Korea": "kr", "Spain": "es", "Sri Lanka": "lk", "Sudan": "sd", "Sweden": "se", "Switzerland": "ch",
        "Syria": "sy","Taiwan": "tw", "Thailand": "th", "Turkey": "tr", "Ukraine": "ua", "United Arab Emirates": "ae", "United Kingdom": "gb",
        "United States": "us", "Uruguay": "uy", "Vatican City": "va", "Venezuela": "ve", "Vietnam": "vn", "Yemen": "ye",
        "Zambia": "zm", "Zimbabwe": "zw"
    };
    return countryCodes[countryName] || "Unknown";
}

// 顯示所有國家的瀏覽數量
async function displayAllVisitorCounts() {
    const visitorCountsElement = document.getElementById('visitor-counts');
    visitorCountsElement.innerHTML = ''; // 清空現有內容

    try {
        const querySnapshot = await getDocs(collection(db, "visitors"));
        querySnapshot.forEach((doc) => {
            const country = doc.id;
            const count = doc.data().count;
            const countryCode = getCountryCode(country);

            if (countryCode !== "Unknown") {
                const div = document.createElement('div');
                div.classList.add('visitor-count-item');
                div.innerHTML = `<span class="fi fi-${countryCode.toLowerCase()}"></span>: ${count}`;
                visitorCountsElement.appendChild(div);
            }
        });
    } catch (error) {
        console.error("Error fetching visitor counts:", error);
    }
}


// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    await updateVisitorCount();
    await displayAllVisitorCounts();
});