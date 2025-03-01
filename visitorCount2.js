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

async function getVisitorCountry() {
    try {
        const response = await fetch('https://ipapi.co/json/');
        const data = await response.json();
        return data.country_name || "Unknown";
    } catch (error) {
        console.error('Error fetching country:', error);
        return "Unknown";
    }
}

async function updateVisitorCount() {
    const country = await getVisitorCountry();
    const visitorRef = doc(db, "visitors", country);

    try {
        const visitorSnap = await getDoc(visitorRef);
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
		
    } catch (error) {
        console.error("Error updating visitor count:", error);
    }
}

function getCountryCode(countryName) {
    const countryCodes = {
        "Afghanistan": "af", "Albania": "al", "Algeria": "dz", "Andorra": "ad", "Angola": "ao", "Antigua and Barbuda": "ag",
        "Argentina": "ar", "Armenia": "am", "Australia": "au", "Austria": "at", "Azerbaijan": "az", "Bahamas": "bs",
        "Bahrain": "bh", "Bangladesh": "bd", "Barbados": "bb", "Belarus": "by", "Belgium": "be", "Belize": "bz",
        "Benin": "bj", "Bhutan": "bt", "Bolivia": "bo", "Bosnia and Herzegovina": "ba", "Botswana": "bw", "Brazil": "br",
        "Brunei": "bn", "Bulgaria": "bg", "Burkina Faso": "bf", "Burundi": "bi", "Cabo Verde": "cv", "Cambodia": "kh",
        "Cameroon": "cm", "Canada": "ca", "Central African Republic": "cf", "Chad": "td", "Chile": "cl", "China": "cn",
        "Colombia": "co", "Comoros": "km", "Congo (Congo-Brazzaville)": "cg", "Congo (Congo-Kinshasa)": "cd", "Costa Rica": "cr",
        "Croatia": "hr", "Cuba": "cu", "Cyprus": "cy", "Czechia": "cz", "Denmark": "dk", "Djibouti": "dj", "Dominica": "dm",
        "Dominican Republic": "do", "Ecuador": "ec", "Egypt": "eg", "El Salvador": "sv", "Equatorial Guinea": "gq", "Eritrea": "er",
        "Estonia": "ee", "Eswatini": "sz", "Ethiopia": "et", "Fiji": "fj", "Finland": "fi", "France": "fr", "Gabon": "ga",
        "Gambia": "gm", "Georgia": "ge", "Germany": "de", "Ghana": "gh", "Greece": "gr", "Grenada": "gd", "Guatemala": "gt",
        "Guinea": "gn", "Guinea-Bissau": "gw", "Guyana": "gy", "Haiti": "ht", "Honduras": "hn", "Hungary": "hu", "Iceland": "is",
        "India": "in", "Indonesia": "id", "Iran": "ir", "Iraq": "iq", "Ireland": "ie", "Israel": "il", "Italy": "it",
        "Jamaica": "jm", "Japan": "jp", "Jordan": "jo", "Kazakhstan": "kz", "Kenya": "ke", "Kiribati": "ki", "Kuwait": "kw",
        "Kyrgyzstan": "kg", "Laos": "la", "Latvia": "lv", "Lebanon": "lb", "Lesotho": "ls", "Liberia": "lr", "Libya": "ly",
        "Liechtenstein": "li", "Lithuania": "lt", "Luxembourg": "lu", "Madagascar": "mg", "Malawi": "mw", "Malaysia": "my",
        "Maldives": "mv", "Mali": "ml", "Malta": "mt", "Marshall Islands": "mh", "Mauritania": "mr", "Mauritius": "mu",
        "Mexico": "mx", "Micronesia": "fm", "Moldova": "md", "Monaco": "mc", "Mongolia": "mn", "Montenegro": "me",
        "Morocco": "ma", "Mozambique": "mz", "Myanmar": "mm", "Namibia": "na", "Nauru": "nr", "Nepal": "np", "Netherlands": "nl",
        "New Zealand": "nz", "Nicaragua": "ni", "Niger": "ne", "Nigeria": "ng", "North Korea": "kp", "North Macedonia": "mk",
        "Norway": "no", "Oman": "om", "Pakistan": "pk", "Palau": "pw", "Palestine": "ps", "Panama": "pa", "Papua New Guinea": "pg",
        "Paraguay": "py", "Peru": "pe", "Philippines": "ph", "Poland": "pl", "Portugal": "pt", "Qatar": "qa", "Romania": "ro",
        "Russia": "ru", "Rwanda": "rw", "Saint Kitts and Nevis": "kn", "Saint Lucia": "lc", "Saint Vincent and the Grenadines": "vc",
        "Samoa": "ws", "San Marino": "sm", "Sao Tome and Principe": "st", "Saudi Arabia": "sa", "Senegal": "sn", "Serbia": "rs",
        "Seychelles": "sc", "Sierra Leone": "sl", "Singapore": "sg", "Slovakia": "sk", "Slovenia": "si", "Solomon Islands": "sb",
        "Somalia": "so", "South Africa": "za", "South Korea": "kr", "South Sudan": "ss", "Spain": "es", "Sri Lanka": "lk",
        "Sudan": "sd", "Suriname": "sr", "Sweden": "se", "Switzerland": "ch", "Syria": "sy", "Tajikistan": "tj", "Tanzania": "tz",
        "Thailand": "th", "Timor-Leste": "tl", "Togo": "tg", "Tonga": "to", "Trinidad and Tobago": "tt", "Tunisia": "tn",
        "Turkey": "tr", "Turkmenistan": "tm", "Tuvalu": "tv", "Uganda": "ug", "Ukraine": "ua", "United Arab Emirates": "ae",
        "United Kingdom": "gb", "United States": "us", "Uruguay": "uy", "Uzbekistan": "uz", "Vanuatu": "vu", "Vatican City": "va",
        "Venezuela": "ve", "Vietnam": "vn", "Yemen": "ye", "Zambia": "zm", "Zimbabwe": "zw"
    };
    return countryCodes[countryName] || "Unknown";
}


async function displayAllVisitorCounts() {
    const visitorCountsElement = document.getElementById('visitor-counts');
    visitorCountsElement.innerHTML = '';

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

document.addEventListener('DOMContentLoaded', async () => {
    await updateVisitorCount();
    await displayAllVisitorCounts();
});
