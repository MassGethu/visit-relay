// Page language. When the speech language changes, every fixed piece of English on the page (buttons,
// labels, status lines, card text, dialogs) switches to Hindi or Kannada. It works on the DOM, so it
// covers text set by app.js and cards.js alike: each text node keeps its English source and is rewritten
// from it. Her own words, AI replies and text that already comes localized from the backend are left alone.
(() => {
  "use strict";

  // English -> [Hindi, Kannada]
  const WORDS = {
    // page frame (index.html)
    "SYNTHETIC DATA": ["सिंथेटिक (नकली) डेटा", "ಸಿಂಥೆಟಿಕ್ (ನಕಲಿ) ಡೇಟಾ"],
    "ASHA Voice Register": ["आशा वॉइस रजिस्टर", "ಆಶಾ ವಾಯ್ಸ್ ರಿಜಿಸ್ಟರ್"],
    "Patient dashboard": ["मरीज़ डैशबोर्ड", "ರೋಗಿಯ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್"],
    "Speech language": ["बोलने की भाषा", "ಮಾತಿನ ಭಾಷೆ"],
    "Hands-free listening": ["हैंड्स-फ़्री", "ಹ್ಯಾಂಡ್ಸ್-ಫ್ರೀ"],
    "Enable microphone": ["माइक चालू करें", "ಮೈಕ್ ಆನ್ ಮಾಡಿ"],
    "Upload MP3 instead": ["MP3 अपलोड करें", "MP3 ಅಪ್‌ಲೋಡ್ ಮಾಡಿ"],
    "Hold to talk": ["दबाकर रखें और बोलें", "ಒತ್ತಿ ಹಿಡಿದು ಮಾತನಾಡಿ"],
    "Listening… let go to send": ["सुन रहा है… भेजने के लिए छोड़ें", "ಆಲಿಸುತ್ತಿದೆ… ಕಳುಹಿಸಲು ಬಿಡಿ"],
    "End visit session": ["विज़िट समाप्त करें", "ಭೇಟಿ ಮುಗಿಸಿ"],
    "Download last turn audio": ["पिछली रिकॉर्डिंग डाउनलोड करें", "ಕೊನೆಯ ರೆಕಾರ್ಡಿಂಗ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ"],
    "Download recording": ["रिकॉर्डिंग डाउनलोड करें", "ರೆಕಾರ್ಡಿಂಗ್ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ"],
    "MP3 upload": ["MP3 अपलोड", "MP3 ಅಪ್‌ಲೋಡ್"],
    "MP3 recordings are transcribed and checked for danger signs when they sync.": [
      "सिंक होने पर MP3 रिकॉर्डिंग लिखी जाती है और खतरे के लक्षण जाँचे जाते हैं।",
      "ಸಿಂಕ್ ಆದಾಗ MP3 ರೆಕಾರ್ಡಿಂಗ್ ಅನ್ನು ಬರೆದು, ಅಪಾಯದ ಲಕ್ಷಣಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತದೆ."],
    "Import an MP3 recording (up to 60 seconds)": ["MP3 रिकॉर्डिंग चुनें (60 सेकंड तक)",
      "MP3 ರೆಕಾರ್ಡಿಂಗ್ ಆಯ್ಕೆಮಾಡಿ (60 ಸೆಕೆಂಡ್‌ವರೆಗೆ)"],
    "Retry sync": ["फिर से सिंक करें", "ಮತ್ತೆ ಸಿಂಕ್ ಮಾಡಿ"],
    "Confirm and save visit": ["पक्का करें और विज़िट सेव करें", "ಖಚಿತಪಡಿಸಿ ಭೇಟಿ ಉಳಿಸಿ"],
    "Remove": ["हटाएँ", "ತೆಗೆದುಹಾಕಿ"],
    "Transcript": ["लिखी हुई बातचीत", "ಮಾತಿನ ಬರಹ"],
    "Transcript speaker": ["किसकी बात", "ಯಾರ ಮಾತು"],
    "Your speech": ["आपकी बात", "ನಿಮ್ಮ ಮಾತು"],
    "AI replies": ["AI के जवाब", "AI ಉತ್ತರಗಳು"],
    "Your words will appear here.": ["आपके शब्द यहाँ दिखेंगे।", "ನಿಮ್ಮ ಮಾತುಗಳು ಇಲ್ಲಿ ಕಾಣುತ್ತವೆ."],
    "AI replies will appear here.": ["AI के जवाब यहाँ दिखेंगे।", "AI ಉತ್ತರಗಳು ಇಲ್ಲಿ ಕಾಣುತ್ತವೆ."],

    // status line (app.js)
    "Enable your microphone to start.": ["शुरू करने के लिए माइक चालू करें।", "ಆರಂಭಿಸಲು ಮೈಕ್ ಆನ್ ಮಾಡಿ."],
    "Allow microphone access in your browser and try again.": ["ब्राउज़र में माइक की अनुमति दें और फिर कोशिश करें।",
      "ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಮೈಕ್ ಅನುಮತಿ ನೀಡಿ, ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."],
    "Audio capture failed. You can still upload an MP3.": ["आवाज़ रिकॉर्ड नहीं हुई। आप MP3 अपलोड कर सकती हैं।",
      "ಧ್ವನಿ ರೆಕಾರ್ಡ್ ಆಗಲಿಲ್ಲ. ನೀವು MP3 ಅಪ್‌ಲೋಡ್ ಮಾಡಬಹುದು."],
    "Audio sent. Hold to talk again.": ["आवाज़ भेज दी गई। फिर बोलने के लिए दबाकर रखें।",
      "ಧ್ವನಿ ಕಳುಹಿಸಲಾಗಿದೆ. ಮತ್ತೆ ಮಾತನಾಡಲು ಒತ್ತಿ ಹಿಡಿಯಿರಿ."],
    "Choose a recording up to 60 seconds long.": ["60 सेकंड तक की रिकॉर्डिंग चुनें।",
      "60 ಸೆಕೆಂಡ್‌ವರೆಗಿನ ರೆಕಾರ್ಡಿಂಗ್ ಆಯ್ಕೆಮಾಡಿ."],
    "Choose an MP3 under 12 MB and up to 60 seconds long.": ["12 MB से छोटी और 60 सेकंड तक की MP3 चुनें।",
      "12 MB ಗಿಂತ ಚಿಕ್ಕ, 60 ಸೆಕೆಂಡ್‌ವರೆಗಿನ MP3 ಆಯ್ಕೆಮಾಡಿ."],
    "Connect once to select a beneficiary and start the visit.": [
      "लाभार्थी चुनने और विज़िट शुरू करने के लिए एक बार इंटरनेट से जुड़ें।",
      "ಫಲಾನುಭವಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ ಭೇಟಿ ಆರಂಭಿಸಲು ಒಮ್ಮೆ ಇಂಟರ್ನೆಟ್‌ಗೆ ಸಂಪರ್ಕಿಸಿ."],
    "Connecting…": ["जुड़ रहा है…", "ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ…"],
    "Connection lost. You can still upload an MP3.": ["कनेक्शन टूट गया। आप MP3 अपलोड कर सकती हैं।",
      "ಸಂಪರ್ಕ ಕಡಿತವಾಯಿತು. ನೀವು MP3 ಅಪ್‌ಲೋಡ್ ಮಾಡಬಹುದು."],
    "Could not clear the saved entries. Try again.": ["सेव की गई एंट्री नहीं हटीं। फिर कोशिश करें।",
      "ಉಳಿಸಿದ ನಮೂದುಗಳನ್ನು ಅಳಿಸಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."],
    "Could not load the demo visit.": ["डेमो विज़िट नहीं खुली।", "ಡೆಮೊ ಭೇಟಿ ತೆರೆಯಲಾಗಲಿಲ್ಲ."],
    "Could not open the visit.": ["विज़िट नहीं खुली।", "ಭೇಟಿ ತೆರೆಯಲಾಗಲಿಲ್ಲ."],
    "Could not restore the local visit. Check browser storage and reload.": [
      "फ़ोन पर रखी विज़िट वापस नहीं आई। ब्राउज़र स्टोरेज जाँचें और पेज फिर से खोलें।",
      "ಫೋನ್‌ನಲ್ಲಿನ ಭೇಟಿಯನ್ನು ಮರಳಿ ತರಲಾಗಲಿಲ್ಲ. ಬ್ರೌಸರ್ ಸ್ಟೋರೇಜ್ ಪರಿಶೀಲಿಸಿ, ಪುಟ ಮತ್ತೆ ತೆರೆಯಿರಿ."],
    "Could not save the visit on this phone.": ["इस फ़ोन पर विज़िट सेव नहीं हुई।", "ಈ ಫೋನ್‌ನಲ್ಲಿ ಭೇಟಿ ಉಳಿಸಲಾಗಲಿಲ್ಲ."],
    "Could not save this entry on the phone.": ["यह एंट्री फ़ोन पर सेव नहीं हुई।", "ಈ ನಮೂದನ್ನು ಫೋನ್‌ನಲ್ಲಿ ಉಳಿಸಲಾಗಲಿಲ್ಲ."],
    "Could not start voice capture. You can upload an MP3 instead.": [
      "आवाज़ रिकॉर्डिंग शुरू नहीं हुई। आप MP3 अपलोड कर सकती हैं।",
      "ಧ್ವನಿ ರೆಕಾರ್ಡಿಂಗ್ ಆರಂಭವಾಗಲಿಲ್ಲ. ಬದಲಿಗೆ MP3 ಅಪ್‌ಲೋಡ್ ಮಾಡಬಹುದು."],
    "Could not update the phone’s saved entries. Retry sync.": [
      "फ़ोन की सेव एंट्री अपडेट नहीं हुईं। फिर से सिंक करें।",
      "ಫೋನ್‌ನ ಉಳಿಸಿದ ನಮೂದುಗಳನ್ನು ನವೀಕರಿಸಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಸಿಂಕ್ ಮಾಡಿ."],
    "Could not update the phone’s saved entries.": ["फ़ोन की सेव एंट्री अपडेट नहीं हुईं।",
      "ಫೋನ್‌ನ ಉಳಿಸಿದ ನಮೂದುಗಳನ್ನು ನವೀಕರಿಸಲಾಗಲಿಲ್ಲ."],
    "Danger sign reported. Refer to PHC.": ["खतरे का लक्षण बताया गया। PHC भेजें।",
      "ಅಪಾಯದ ಲಕ್ಷಣ ತಿಳಿಸಲಾಗಿದೆ. PHC ಗೆ ಕಳುಹಿಸಿ."],
    "Hold to talk.": ["बोलने के लिए दबाकर रखें।", "ಮಾತನಾಡಲು ಒತ್ತಿ ಹಿಡಿಯಿರಿ."],
    "Listening hands-free…": ["बिना दबाए सुन रहा है…", "ಹ್ಯಾಂಡ್ಸ್-ಫ್ರೀ ಆಲಿಸುತ್ತಿದೆ…"],
    "Listening…": ["सुन रहा है…", "ಆಲಿಸುತ್ತಿದೆ…"],
    "MP3 recordings sync automatically.": ["MP3 रिकॉर्डिंग अपने-आप सिंक होंगी।",
      "MP3 ರೆಕಾರ್ಡಿಂಗ್‌ಗಳು ತಾನಾಗಿಯೇ ಸಿಂಕ್ ಆಗುತ್ತವೆ."],
    "Microphone access requires HTTPS. You can start without a microphone.": [
      "माइक के लिए HTTPS चाहिए। आप बिना माइक के शुरू कर सकती हैं।", "ಮೈಕ್‌ಗೆ HTTPS ಬೇಕು. ಮೈಕ್ ಇಲ್ಲದೆಯೂ ಆರಂಭಿಸಬಹುದು."],
    "Microphone will resume when connected.": ["जुड़ने पर माइक फिर चालू होगा।", "ಸಂಪರ್ಕವಾದಾಗ ಮೈಕ್ ಮತ್ತೆ ಆರಂಭವಾಗುತ್ತದೆ."],
    "No speech transcribed. Hold to talk and try again.": ["कोई बात सुनाई नहीं दी। दबाकर रखें और फिर बोलें।",
      "ಯಾವುದೇ ಮಾತು ಕೇಳಿಸಲಿಲ್ಲ. ಒತ್ತಿ ಹಿಡಿದು ಮತ್ತೆ ಮಾತನಾಡಿ."],
    "No synthetic beneficiary is available.": ["कोई सिंथेटिक लाभार्थी उपलब्ध नहीं है।", "ಯಾವುದೇ ಸಿಂಥೆಟಿಕ್ ಫಲಾನುಭವಿ ಲಭ್ಯವಿಲ್ಲ."],
    "Offline. MP3 recordings will sync when connected.": ["ऑफ़लाइन। जुड़ने पर MP3 रिकॉर्डिंग सिंक होंगी।",
      "ಆಫ್‌ಲೈನ್. ಸಂಪರ್ಕವಾದಾಗ MP3 ರೆಕಾರ್ಡಿಂಗ್‌ಗಳು ಸಿಂಕ್ ಆಗುತ್ತವೆ."],
    "Offline. You can still work on this visit.": ["ऑफ़लाइन। आप यह विज़िट जारी रख सकती हैं।",
      "ಆಫ್‌ಲೈನ್. ಈ ಭೇಟಿಯನ್ನು ಮುಂದುವರಿಸಬಹುದು."],
    "Opening microphone…": ["माइक खुल रहा है…", "ಮೈಕ್ ತೆರೆಯುತ್ತಿದೆ…"],
    "Preparing the recording on this phone…": ["इस फ़ोन पर रिकॉर्डिंग तैयार हो रही है…",
      "ಈ ಫೋನ್‌ನಲ್ಲಿ ರೆಕಾರ್ಡಿಂಗ್ ಸಿದ್ಧವಾಗುತ್ತಿದೆ…"],
    "Ready to talk.": ["बोलने के लिए तैयार।", "ಮಾತನಾಡಲು ಸಿದ್ಧ."],
    "Sending audio…": ["आवाज़ भेजी जा रही है…", "ಧ್ವನಿ ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ…"],
    "Slow network or reply. Still processing…": ["नेटवर्क या जवाब धीमा है। अभी काम चल रहा है…",
      "ನೆಟ್‌ವರ್ಕ್ ಅಥವಾ ಉತ್ತರ ನಿಧಾನವಾಗಿದೆ. ಇನ್ನೂ ನಡೆಯುತ್ತಿದೆ…"],
    "Speaking. Hold to interrupt.": ["बोल रहा है। रोकने के लिए दबाकर रखें।", "ಮಾತನಾಡುತ್ತಿದೆ. ನಿಲ್ಲಿಸಲು ಒತ್ತಿ ಹಿಡಿಯಿರಿ."],
    "Speaking. Listening will resume.": ["बोल रहा है। उसके बाद फिर सुनेगा।", "ಮಾತನಾಡುತ್ತಿದೆ. ನಂತರ ಮತ್ತೆ ಆಲಿಸುತ್ತದೆ."],
    "Sync the current entries before adding more.": ["और जोड़ने से पहले अभी की एंट्री सिंक करें।",
      "ಇನ್ನಷ್ಟು ಸೇರಿಸುವ ಮೊದಲು ಈಗಿನ ನಮೂದುಗಳನ್ನು ಸಿಂಕ್ ಮಾಡಿ."],
    "Syncing visit entries…": ["विज़िट की एंट्री सिंक हो रही हैं…", "ಭೇಟಿ ನಮೂದುಗಳು ಸಿಂಕ್ ಆಗುತ್ತಿವೆ…"],
    "The browser interrupted this hold. Try again.": ["ब्राउज़र ने बीच में रोक दिया। फिर कोशिश करें।",
      "ಬ್ರೌಸರ್ ಮಧ್ಯದಲ್ಲಿ ನಿಲ್ಲಿಸಿತು. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."],
    "The microphone stopped. You can still upload an MP3.": ["माइक बंद हो गया। आप MP3 अपलोड कर सकती हैं।",
      "ಮೈಕ್ ನಿಂತುಹೋಯಿತು. ನೀವು MP3 ಅಪ್‌ಲೋಡ್ ಮಾಡಬಹುದು."],
    "The server draft is unavailable. Unsynced entries are still on this phone.": [
      "सर्वर पर ड्राफ़्ट नहीं मिला। बिना सिंक की एंट्री इसी फ़ोन पर हैं।",
      "ಸರ್ವರ್ ಡ್ರಾಫ್ಟ್ ಲಭ್ಯವಿಲ್ಲ. ಸಿಂಕ್ ಆಗದ ನಮೂದುಗಳು ಈ ಫೋನ್‌ನಲ್ಲೇ ಇವೆ."],
    "This browser could not read that MP3.": ["यह ब्राउज़र वह MP3 नहीं पढ़ सका।", "ಈ ಬ್ರೌಸರ್ ಆ MP3 ಓದಲಾಗಲಿಲ್ಲ."],
    "Visit restored.": ["विज़िट वापस आ गई।", "ಭೇಟಿ ಮರಳಿ ತೆರೆಯಲಾಗಿದೆ."],
    "Visit session ended. Start again when ready.": ["विज़िट समाप्त। तैयार हों तो फिर शुरू करें।",
      "ಭೇಟಿ ಮುಗಿಯಿತು. ಸಿದ್ಧವಾದಾಗ ಮತ್ತೆ ಆರಂಭಿಸಿ."],
    "Waiting for a connection…": ["कनेक्शन का इंतज़ार…", "ಸಂಪರ್ಕಕ್ಕಾಗಿ ಕಾಯುತ್ತಿದೆ…"],
    "Waiting for the AI disclosure…": ["AI की सूचना का इंतज़ार…", "AI ಸೂಚನೆಗಾಗಿ ಕಾಯುತ್ತಿದೆ…"],
    "Remove this unsynced entry from the phone?": ["बिना सिंक की यह एंट्री फ़ोन से हटाएँ?",
      "ಸಿಂಕ್ ಆಗದ ಈ ನಮೂದನ್ನು ಫೋನ್‌ನಿಂದ ತೆಗೆಯಬೇಕೆ?"],
    "End the visit session and discard unsynced entries?": ["विज़िट समाप्त करें और बिना सिंक की एंट्री हटा दें?",
      "ಭೇಟಿ ಮುಗಿಸಿ, ಸಿಂಕ್ ಆಗದ ನಮೂದುಗಳನ್ನು ತೆಗೆಯಬೇಕೆ?"],

    // visit header (cards.js)
    "Visit": ["विज़िट", "ಭೇಟಿ"],
    "Synthetic beneficiary": ["सिंथेटिक लाभार्थी", "ಸಿಂಥೆಟಿಕ್ ಫಲಾನುಭವಿ"],
    "Discreet mode": ["गुप्त मोड", "ಗುಪ್ತ ಮೋಡ್"],
    "Who are you visiting?": ["आप किससे मिल रही हैं?", "ನೀವು ಯಾರನ್ನು ಭೇಟಿ ಮಾಡುತ್ತಿದ್ದೀರಿ?"],
    "Visit type": ["विज़िट का प्रकार", "ಭೇಟಿಯ ಪ್ರಕಾರ"],
    "ANC · pregnancy": ["ANC · गर्भावस्था", "ANC · ಗರ್ಭಾವಸ್ಥೆ"],
    "PNC · mother after delivery": ["PNC · प्रसव के बाद माँ", "PNC · ಹೆರಿಗೆಯ ನಂತರ ತಾಯಿ"],
    "HBNC · newborn": ["HBNC · नवजात शिशु", "HBNC · ನವಜಾತ ಶಿಶು"],
    "HBYC · young child": ["HBYC · छोटा बच्चा", "HBYC · ಚಿಕ್ಕ ಮಗು"],
    "Could not change the visit type. Try again.": ["विज़िट का प्रकार नहीं बदला। फिर कोशिश करें।",
      "ಭೇಟಿಯ ಪ್ರಕಾರ ಬದಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."],
    "Which visit is this?": ["यह कौन-सी विज़िट है?", "ಇದು ಯಾವ ಭೇಟಿ?"],
    "Answer by voice, or tap:": ["बोलकर जवाब दें, या दबाएँ:", "ಮಾತಿನಲ್ಲಿ ಉತ್ತರಿಸಿ, ಅಥವಾ ಒತ್ತಿ:"],

    // alerts and live cards
    "Danger sign": ["खतरे का लक्षण", "ಅಪಾಯದ ಲಕ್ಷಣ"],
    "Refer to PHC": ["PHC भेजें", "PHC ಗೆ ಕಳುಹಿಸಿ"],
    "Flagged for ANM": ["ANM को बताया गया", "ANM ಗೆ ತಿಳಿಸಲಾಗಿದೆ"],
    "Noted — say “ANM ko batao” to flag": ["नोट किया — ANM को बताने के लिए “ANM ko batao” बोलें",
      "ಗಮನಿಸಲಾಗಿದೆ — ANM ಗೆ ತಿಳಿಸಲು “ANM ko batao” ಎಂದು ಹೇಳಿ"],
    "Measurements": ["माप", "ಅಳತೆಗಳು"],
    "Not recorded": ["दर्ज नहीं", "ದಾಖಲಾಗಿಲ್ಲ"],
    "Pregnancy month": ["गर्भ का महीना", "ಗರ್ಭದ ತಿಂಗಳು"],
    "Weight": ["वज़न", "ತೂಕ"],
    "Temperature": ["तापमान", "ತಾಪಮಾನ"],
    "Breathing": ["साँस", "ಉಸಿರಾಟ"],
    "Next visit": ["अगली विज़िट", "ಮುಂದಿನ ಭೇಟಿ"],
    "Next visit (said)": ["अगली विज़िट (जैसा बोला)", "ಮುಂದಿನ ಭೇಟಿ (ಹೇಳಿದಂತೆ)"],
    "IFA tablets": ["IFA गोलियाँ", "IFA ಮಾತ್ರೆಗಳು"],
    "Taking": ["ले रही हैं", "ತಿನ್ನುತ್ತಿದ್ದಾರೆ"],
    "Not taking": ["नहीं ले रहीं", "ತಿನ್ನುತ್ತಿಲ್ಲ"],
    "Vaccines given": ["लगे टीके", "ನೀಡಿದ ಲಸಿಕೆಗಳು"],
    "Vaccines due": ["बाकी टीके", "ಬಾಕಿ ಲಸಿಕೆಗಳು"],
    "Danger-sign questions": ["खतरे के लक्षणों के सवाल", "ಅಪಾಯದ ಲಕ್ಷಣಗಳ ಪ್ರಶ್ನೆಗಳು"],
    "Questions answered": ["जवाब दिए गए सवाल", "ಉತ್ತರಿಸಿದ ಪ್ರಶ್ನೆಗಳು"],
    "Dictate what you know. Say “not sure” for a question you cannot answer.": [
      "जो पता है, बोलें। जिस सवाल का जवाब न पता हो, उस पर “पता नहीं” बोलें।",
      "ಗೊತ್ತಿರುವುದನ್ನು ಹೇಳಿ. ಉತ್ತರ ಗೊತ್ತಿಲ್ಲದ ಪ್ರಶ್ನೆಗೆ “ಗೊತ್ತಿಲ್ಲ” ಎನ್ನಿ."],
    "Asking now": ["अभी पूछ रहे हैं", "ಈಗ ಕೇಳುತ್ತಿದೆ"],
    "Present": ["है", "ಇದೆ"],
    "Ruled out": ["नहीं है", "ಇಲ್ಲ"],
    "Not checked": ["नहीं पूछा", "ಕೇಳಿಲ್ಲ"],
    "present": ["है", "ಇದೆ"],
    "ruled out": ["नहीं है", "ಇಲ್ಲ"],
    "not checked": ["नहीं पूछा", "ಕೇಳಿಲ್ಲ"],
    "Loading safety questions…": ["सवाल आ रहे हैं…", "ಪ್ರಶ್ನೆಗಳು ಬರುತ್ತಿವೆ…"],
    "Could not load safety questions.": ["सवाल नहीं आ सके।", "ಪ್ರಶ್ನೆಗಳನ್ನು ತರಲಾಗಲಿಲ್ಲ."],
    "Danger report": ["खतरे की रिपोर्ट", "ಅಪಾಯದ ವರದಿ"],
    "Danger report preview": ["खतरे की रिपोर्ट", "ಅಪಾಯದ ವರದಿ"],
    "Sign counts": ["लक्षणों की गिनती", "ಲಕ್ಷಣಗಳ ಎಣಿಕೆ"],
    "Review the cited flags and the PHC referral shown above.": ["ऊपर दिखाए लक्षण और PHC रेफ़रल देखें।",
      "ಮೇಲೆ ತೋರಿಸಿದ ಲಕ್ಷಣಗಳು ಮತ್ತು PHC ರೆಫರಲ್ ನೋಡಿ."],
    "No checklist signs flagged. Review anything still unchecked.": [
      "कोई खतरे का लक्षण नहीं मिला। जो नहीं पूछा, उसे देख लें।", "ಯಾವುದೇ ಅಪಾಯದ ಲಕ್ಷಣ ಕಂಡಿಲ್ಲ. ಕೇಳದೆ ಉಳಿದವನ್ನು ನೋಡಿ."],
    "Review all signs": ["सभी लक्षण देखें", "ಎಲ್ಲಾ ಲಕ್ಷಣಗಳನ್ನು ನೋಡಿ"],
    "Speaking": ["बोल रहा है", "ಮಾತನಾಡುತ್ತಿದೆ"],
    "Your turn": ["अब आप बोलें", "ಈಗ ನೀವು ಹೇಳಿ"],
    "Visit record": ["विज़िट रिकॉर्ड", "ಭೇಟಿ ದಾಖಲೆ"],
    "Also recorded": ["और भी दर्ज", "ಇನ್ನೂ ದಾಖಲಾಗಿದೆ"],
    "Worker concerns (her words)": ["ASHA की चिंताएँ (उनके शब्द)", "ASHA ಕಾಳಜಿಗಳು (ಅವರ ಮಾತುಗಳು)"],
    "Flagged before the visit type changed": ["विज़िट का प्रकार बदलने से पहले मिले लक्षण",
      "ಭೇಟಿಯ ಪ್ರಕಾರ ಬದಲಾಗುವ ಮೊದಲು ಕಂಡ ಲಕ್ಷಣಗಳು"],

    // end of visit
    "Disputed — ANM to check": ["विवादित — ANM जाँचेंगी", "ವಿವಾದಿತ — ANM ಪರಿಶೀಲಿಸುತ್ತಾರೆ"],
    "Happened earlier": ["पहले हुआ था", "ಮೊದಲು ಆಗಿತ್ತು"],
    "Danger-sign receipt": ["खतरे के लक्षणों की रसीद", "ಅಪಾಯದ ಲಕ್ಷಣಗಳ ರಸೀದಿ"],
    "No danger sign was discussed.": ["किसी खतरे के लक्षण पर बात नहीं हुई।", "ಯಾವುದೇ ಅಪಾಯದ ಲಕ್ಷಣದ ಬಗ್ಗೆ ಮಾತಾಗಿಲ್ಲ."],
    "Spoken by: ASHA": ["बोलने वाली: ASHA", "ಹೇಳಿದವರು: ASHA"],
    "ANM referral card": ["ANM रेफ़रल कार्ड", "ANM ರೆಫರಲ್ ಕಾರ್ಡ್"],
    "ANM / PHC card": ["ANM / PHC कार्ड", "ANM / PHC ಕಾರ್ಡ್"],
    "No checklist signs flagged.": ["कोई खतरे का लक्षण नहीं मिला।", "ಯಾವುದೇ ಅಪಾಯದ ಲಕ್ಷಣ ಕಂಡಿಲ್ಲ."],
    "Worker concern — ASHA asked ANM to review": ["ASHA की चिंता — ANM से जाँचने को कहा",
      "ASHA ಕಾಳಜಿ — ANM ಪರಿಶೀಲಿಸಲು ಕೇಳಿದ್ದಾರೆ"],
    "No diagnosis made by AI. Synthetic data.": ["AI ने कोई निदान नहीं किया। सिंथेटिक डेटा।",
      "AI ಯಾವುದೇ ರೋಗನಿರ್ಣಯ ಮಾಡಿಲ್ಲ. ಸಿಂಥೆಟಿಕ್ ಡೇಟಾ."],
    "Save undone. Tell me what to change.": ["सेव रद्द किया। बताइए क्या बदलना है।",
      "ಉಳಿಸಿದ್ದು ರದ್ದಾಗಿದೆ. ಏನು ಬದಲಾಯಿಸಬೇಕು ಹೇಳಿ."],
    "Visit saved": ["विज़िट सेव हो गई", "ಭೇಟಿ ಉಳಿಸಲಾಗಿದೆ"],
    "Show ANM card": ["ANM कार्ड दिखाएँ", "ANM ಕಾರ್ಡ್ ತೋರಿಸಿ"],
    "Hide ANM card": ["ANM कार्ड छिपाएँ", "ANM ಕಾರ್ಡ್ ಮರೆಮಾಡಿ"],

    // patient progress report
    "Confirmed visit report": ["पक्की विज़िट रिपोर्ट", "ಖಚಿತ ಭೇಟಿ ವರದಿ"],
    "Patient progress": ["मरीज़ की प्रगति", "ರೋಗಿಯ ಪ್ರಗತಿ"],
    "This is the first recorded visit of this type.": ["इस प्रकार की यह पहली दर्ज विज़िट है।",
      "ಈ ಪ್ರಕಾರದ ಮೊದಲ ದಾಖಲಾದ ಭೇಟಿ ಇದು."],
    "No matching measurements to compare.": ["तुलना के लिए मिलते-जुलते माप नहीं हैं।", "ಹೋಲಿಸಲು ಹೊಂದುವ ಅಳತೆಗಳಿಲ್ಲ."],
    "Danger-sign follow-up": ["खतरे के लक्षणों का फ़ॉलो-अप", "ಅಪಾಯದ ಲಕ್ಷಣಗಳ ಅನುಸರಣೆ"],
    "Preparing report…": ["रिपोर्ट तैयार हो रही है…", "ವರದಿ ಸಿದ್ಧವಾಗುತ್ತಿದೆ…"],
    "Reload report": ["रिपोर्ट फिर से लाएँ", "ವರದಿ ಮತ್ತೆ ತೆರೆಯಿರಿ"],
    "Filing report…": ["रिपोर्ट भेजी जा रही है…", "ವರದಿ ಕಳುಹಿಸಲಾಗುತ್ತಿದೆ…"],
    "Push to dashboard": ["डैशबोर्ड पर भेजें", "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗೆ ಕಳುಹಿಸಿ"],
    "Open patient history": ["मरीज़ का इतिहास खोलें", "ರೋಗಿಯ ಇತಿಹಾಸ ತೆರೆಯಿರಿ"],
    "Could not load the confirmed report.": ["पक्की रिपोर्ट नहीं आ सकी।", "ಖಚಿತ ವರದಿ ತರಲಾಗಲಿಲ್ಲ."],
    "Dashboard filing failed. Try again.": ["डैशबोर्ड पर नहीं भेजा जा सका। फिर कोशिश करें।",
      "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗೆ ಕಳುಹಿಸಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."],
    "Newly reported": ["नया बताया गया", "ಹೊಸದಾಗಿ ತಿಳಿಸಲಾಗಿದೆ"],
    "Reported again": ["फिर से बताया गया", "ಮತ್ತೆ ತಿಳಿಸಲಾಗಿದೆ"],
    "Reported this visit": ["इस विज़िट में बताया गया", "ಈ ಭೇಟಿಯಲ್ಲಿ ತಿಳಿಸಲಾಗಿದೆ"],
    "Previously reported, not checked this visit": ["पहले बताया था, इस बार नहीं पूछा", "ಮೊದಲು ತಿಳಿಸಿದ್ದು, ಈ ಬಾರಿ ಕೇಳಿಲ್ಲ"],
    "Previously reported, answered No this visit": ["पहले बताया था, इस बार “नहीं” कहा",
      "ಮೊದಲು ತಿಳಿಸಿದ್ದು, ಈ ಬಾರಿ “ಇಲ್ಲ” ಎಂದರು"],
    "Higher": ["ज़्यादा", "ಹೆಚ್ಚು"],
    "Lower": ["कम", "ಕಡಿಮೆ"],
    "Same": ["उतना ही", "ಅಷ್ಟೇ"],
    "Changed": ["बदला", "ಬದಲಾಗಿದೆ"],
    "to": ["से", "ಇಂದ"],
  };

  // Sentences with a changing part. "$1" is the part; parts are translated too when they match.
  const PATTERNS = [
    [/^(\d+) saved on this phone\. They’ll sync when connected\.$/u,
      ["$1 इस फ़ोन पर सेव हैं। जुड़ने पर सिंक होंगी।", "$1 ಈ ಫೋನ್‌ನಲ್ಲಿ ಉಳಿದಿವೆ. ಸಂಪರ್ಕವಾದಾಗ ಸಿಂಕ್ ಆಗುತ್ತವೆ."]],
    [/^Download last turn audio \((.+) s\)$/u, ["पिछली रिकॉर्डिंग डाउनलोड करें ($1 से.)", "ಕೊನೆಯ ರೆಕಾರ್ಡಿಂಗ್ ಡೌನ್‌ಲೋಡ್ ($1 ಸೆ.)"]],
    [/^Prisma latency · (.+)$/u, ["Prisma देरी · $1", "Prisma ವಿಳಂಬ · $1"]],
    [/^First reply · (.+)$/u, ["पहला जवाब · $1", "ಮೊದಲ ಉತ್ತರ · $1"]],
    [/^Switching to (.+)…$/u, ["$1 पर बदल रहे हैं…", "$1 ಗೆ ಬದಲಾಯಿಸಲಾಗುತ್ತಿದೆ…"]],
    [/^Changed from (.+)\. Everything said so far was checked again\.$/u,
      ["$1 से बदला गया। अब तक कही हर बात फिर से जाँची गई।", "$1 ಇಂದ ಬದಲಾಯಿಸಲಾಗಿದೆ. ಇಲ್ಲಿಯವರೆಗೆ ಹೇಳಿದ್ದೆಲ್ಲವನ್ನೂ ಮತ್ತೆ ಪರಿಶೀಲಿಸಲಾಗಿದೆ."]],
    [/^Keep (.+)$/u, ["$1 ही रखें", "$1 ಇರಲಿ"]],
    [/^Switch to (.+)$/u, ["$1 पर बदलें", "$1 ಗೆ ಬದಲಾಯಿಸಿ"]],
    [/^Source: (.*)$/u, ["स्रोत: $1", "ಮೂಲ: $1"]],
    [/^(\d+) of (\d+) answered$/u, ["$2 में से $1 के जवाब", "$2 ರಲ್ಲಿ $1 ಉತ್ತರಿಸಲಾಗಿದೆ"]],
    [/^(\d+) of (\d+)$/u, ["$2 में से $1", "$2 ರಲ್ಲಿ $1"]],
    [/^Question (\d+) of (\d+)$/u, ["सवाल $1 / $2", "ಪ್ರಶ್ನೆ $1 / $2"]],
    [/^Dictate what you know\. For each one: (.+)$/su, ["जो पता है, बोलें। हर सवाल पर: $1", "ಗೊತ್ತಿರುವುದನ್ನು ಹೇಳಿ. ಪ್ರತಿಯೊಂದಕ್ಕೂ: $1"], "raw"],
    [/^(.+) — refer to PHC$/u, ["$1 — PHC भेजें", "$1 — PHC ಗೆ ಕಳುಹಿಸಿ"]],
    [/^(\d+) signs not checked \(not asked — never a “No”\)$/u,
      ["$1 लक्षण नहीं पूछे (न पूछना कभी “नहीं” नहीं होता)", "$1 ಲಕ್ಷಣಗಳನ್ನು ಕೇಳಿಲ್ಲ (ಕೇಳದಿರುವುದು ಎಂದಿಗೂ “ಇಲ್ಲ” ಅಲ್ಲ)"]],
    [/^Time: (.+)$/u, ["समय: $1", "ಸಮಯ: $1"]],
    [/^ASHA said: “(.*)”$/su, ["ASHA ने कहा: “$1”", "ASHA ಹೇಳಿದರು: “$1”"], "raw"],
    [/^Recorded: (.+)$/u, ["दर्ज: $1", "ದಾಖಲಾಗಿದೆ: $1"]],
    [/^Last checked (.+)$/u, ["पिछली जाँच $1", "ಕೊನೆಯ ಪರಿಶೀಲನೆ $1"]],
    [/^since synthetic baseline, (.+)$/u, ["सिंथेटिक शुरुआती रिकॉर्ड ($1) से", "ಸಿಂಥೆಟಿಕ್ ಆರಂಭಿಕ ದಾಖಲೆ ($1) ಇಂದ"]],
    [/^since (.+)$/u, ["$1 से", "$1 ಇಂದ"]],
    [/^Compared with the synthetic baseline, (.+)\.$/u,
      ["सिंथेटिक शुरुआती रिकॉर्ड ($1) से तुलना।", "ಸಿಂಥೆಟಿಕ್ ಆರಂಭಿಕ ದಾಖಲೆ ($1) ಜೊತೆ ಹೋಲಿಕೆ."]],
    [/^Compared with the most recent earlier visit, (.+)\.$/u,
      ["पिछली विज़िट ($1) से तुलना।", "ಹಿಂದಿನ ಭೇಟಿ ($1) ಜೊತೆ ಹೋಲಿಕೆ."]],
    // lists like "Weight: 52 kg · BP: 120/80": translate each piece
    [/^([^:·]+): (.+)$/u, ["$1: $2", "$1: $2"]],
    [/^(.+?) · (.+)$/u, ["$1 · $2", "$1 · $2"]],
  ];

  const LANG_INDEX = { hi: 0, kn: 1 };
  const SKIP = "#transcript, #assistant-transcript, #speech-language, .c-quote, .c-said, .c-q, "
    + ".c-question-text, .c-hint, script, style, [data-no-i18n]";
  const ATTRS = ["aria-label", "title", "placeholder"];

  const select = document.querySelector("#speech-language");
  let lang = "en";

  function translate(text, target = lang) {
    const i = LANG_INDEX[target];
    if (i === undefined || !text) return text;
    const core = text.trim();
    if (!core) return text;
    const done = (out) => out === core ? text : text.replace(core, () => out);
    if (Object.hasOwn(WORDS, core)) return done(WORDS[core][i]);
    for (const [re, outs, raw] of PATTERNS) {
      const m = core.match(re);
      if (!m) continue;
      return done(outs[i].replace(/\$(\d)/g, (_, n) => (raw ? m[n] ?? "" : translate(m[n] ?? "", target))));
    }
    return text;
  }

  // Each text node / attribute remembers its English source and what we last wrote into it.
  const textSource = new WeakMap();
  const attrSource = new WeakMap();

  function skipped(node) {
    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    return !element || Boolean(element.closest(SKIP));
  }

  // Inside her words / AI replies only fixed text changes: placeholders ("Your words will appear here.")
  // and the "ASHA said:" lead-in, never the quote itself.
  const placeholder = text => (Object.hasOwn(WORDS, text.trim()) || /^\s*ASHA said: “/u.test(text)
    ? translate(text) : text);

  function fixText(node) {
    if (!node.parentElement) return;
    const seen = textSource.get(node);
    const source = seen && node.data === seen.out ? seen.source : node.data;
    const out = skipped(node) ? placeholder(source) : translate(source);
    if (out !== node.data) node.data = out;
    textSource.set(node, { source, out });
  }

  function fixAttr(element, name) {
    if (!element.hasAttribute(name) || skipped(element)) return;
    const map = attrSource.get(element) || new Map();
    const value = element.getAttribute(name);
    const seen = map.get(name);
    const source = seen && value === seen.out ? seen.source : value;
    const out = translate(source);
    if (out !== value) element.setAttribute(name, out);
    map.set(name, { source, out });
    attrSource.set(element, map);
  }

  function fixTree(root) {
    if (root.nodeType === Node.TEXT_NODE) return fixText(root);
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    for (const name of ATTRS) fixAttr(root, name);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === Node.TEXT_NODE) fixText(node);
      else for (const name of ATTRS) fixAttr(node, name);
    }
  }

  let englishTitle = document.title;
  function applyAll() {
    lang = select && select.value in LANG_INDEX ? select.value : "en";
    document.documentElement.lang = lang;
    document.title = translate(englishTitle);
    const talk = document.querySelector("#talk");
    if (talk) talk.dataset.listening = translate("Listening… let go to send");
    fixTree(document.body);
    window.dispatchEvent(new CustomEvent("i18n:change", { detail: { lang } }));
  }

  const observer = new MutationObserver((records) => {
    // app.js can set the language without a change event (restoring a saved visit).
    if (select && (select.value in LANG_INDEX ? select.value : "en") !== lang) return applyAll();
    for (const record of records) {
      if (record.type === "characterData") fixText(record.target);
      else if (record.type === "attributes") fixAttr(record.target, record.attributeName);
      else record.addedNodes.forEach(fixTree);
    }
  });
  observer.observe(document.body, { subtree: true, childList: true, characterData: true,
    attributes: true, attributeFilter: ATTRS });

  select?.addEventListener("change", applyAll);

  // Dialogs from app.js speak her language too.
  const nativeConfirm = window.confirm.bind(window);
  const nativeAlert = window.alert.bind(window);
  window.confirm = message => nativeConfirm(translate(String(message ?? "")));
  window.alert = message => nativeAlert(translate(String(message ?? "")));

  const LOCALES = { hi: "hi-IN", kn: "kn-IN", en: "en-IN" };
  window.I18n = { translate, lang: () => lang, locale: () => LOCALES[lang] };
  applyAll();
})();
