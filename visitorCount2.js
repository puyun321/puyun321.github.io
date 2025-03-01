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
        if (visitorSnap.exists()) {
            await updateDoc(visitorRef, { count: increment(1) });
        } else {
            await setDoc(visitorRef, { count: 1 });
        }
    } catch (error) {
        console.error("Error updating visitor count:", error);
    }
}

function getCountryCode(countryName) {
    const countryCodes = {
        "Canada": "ca", "China": "cn", "Japan": "jp", "Malaysia": "my", "Taiwan": "tw", "United Kingdom": "gb", "United States": "us",
        "France": "fr", "Germany": "de", "Italy": "it", "Netherlands": "nl", "Finland": "fi", "Sweden": "se", "Austria": "at", "Europe Other": "eu"
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
