# 02: ASHA field vocabulary, spoken numbers and dates (Hindi and Kannada)

Research date: 13 November 2026. Scope: Topic 3 (ASR vocabulary and UIP reference schedule) and Topic 4 (spoken numbers, dates and measurements, and the TTS verbalisation rules).

Labels used in this file:
- **[S#]** points to a numbered entry in the Sources section.
- **SECONDARY**: a non-government or non-WHO source.
- **UNVERIFIED**: a claim no source in this pass could confirm.
- **UNSOURCED-linguistic**: a word form taken from general knowledge of Hindi or Kannada, not from a citable source. Native speakers (ideally Karnataka ASHAs) need to validate these before they are used.

---

## Summary

- **The STT setup decides what the normaliser has to parse.** In Gnani Prisma v3.0, `keyterms` takes up to 200 words or short phrases as a JSON array (`bias_list` is the older name for the same field). With a single `kn-IN`, `indic-auto` or `codemix`, numbers come back **as native words**, not digits. Only a single `hi-IN`/`en-IN` defaults to digits [S9]. The normaliser therefore has to parse Kannada and Hindi number words, so send `format` explicitly.
- **The vocabulary list has 199 terms.** They are programme names, vaccines, medicines, tests, registers, Karnataka-specific names (Thayi card, Madilu, Prasooti Araike) and local words. The ranking is **not frequency-measured**: it was built from programme documents (UIP, HBNC/HBYC, Anemia Mukt Bharat, Karnataka schemes). Almost all Hindi and Kannada spoken forms and misrecognitions are UNSOURCED-linguistic and need field validation.
- **UIP schedule.** It was taken from the MoHFW/NHM National Immunization Schedule [S1] and checked against the PIB factsheet of 17 March 2026 [S2]. Sources disagree on fIPV-3 at 9 to 12 months (rolled out January 2023 per state reports [S4], but missing from the 2026 PIB table) and on PCV coverage (state-limited in the 2020 PDF, listed as universal in 2026). HPV for girls aged 14 was launched as a campaign on 28 February 2026 [S2]. The table is for reference only, and the assistant must never compute due dates from it.
- **Gnani's TTS docs contradict themselves.** One page says text normalisation is automatic, while the inference page says to pass numbers and dates as words [S10][S11]. Kannada normalisation is "under continuous refinement" [S10]. **Decision: pre-verbalise all numbers and dates ourselves**, using the tables below.
- **Main ambiguities the normaliser must handle:**
  - Hindi `kal` and `parson` (past or future, decided by verb tense).
  - Fractional quantifiers (`sava`, `paune`, `saadhe`, `dedh`, `dhai`; Kannada `-vare`, `kaal`, `mukkaal`).
  - Kilo plus gram compounds.
  - BP "X by Y".
  - Day-only dates ("15 tareekh") that have no month.

---

## Topic 3. ASHA field vocabulary (CSV)

How the list was built:
1. **Sources for the terms.** Canonical terms come from:
   - the UIP schedule [S1][S2];
   - HBNC/HBYC visit structure [S6][S7];
   - Anemia Mukt Bharat IFA colour coding [S8];
   - Karnataka maternal schemes [S12][S13][S14].
   Other common NHM programme names (JSY, JSSK, PMSMA, RBSK and so on) are standard NHM nomenclature. They were **not individually re-verified in this pass** (UNVERIFIED for exact current scheme status).
2. **Spoken forms.** `hi_spoken` gives Devanagari followed by romanisation in parentheses, and `kn_spoken` gives Kannada script followed by romanisation. Alternatives are separated by `;`. **All spoken forms and all `variants` are UNSOURCED-linguistic** unless the canonical row is itself a local word cited above. The variants are *predicted* ASR confusions based on how English acronyms are spelled out letter by letter in Indian English, Hindi and Kannada. They are not observed error logs.
3. **Rough priority.** Rows are grouped by category. The first 200 Prisma `keyterms` should be chosen from the canonical column plus the native-script forms of the local words (see Risks, item 2).

```csv
canonical,hi_spoken,kn_spoken,variants
ASHA,आशा (aasha); आशा दीदी (aasha didi),ಆಶಾ (aasha); ಆಶಾ ಕಾರ್ಯಕರ್ತೆ (aasha kaaryakarte),asha; aasa; aashaa; अशा
ANM,ए एन एम (e en em); सिस्टर (sister); बहनजी (bahenji),ಎ ಎನ್ ಎಮ್ (e en em); ಸಿಸ್ಟರ್ (sister); ನರ್ಸ್ (nurse),a n m; anem; एनम; enam; and em
Anganwadi worker (AWW),आंगनवाड़ी दीदी (aanganwaadi didi); आंगनवाड़ी वाली (aanganwaadi waali),ಅಂಗನವಾಡಿ ಕಾರ್ಯಕರ್ತೆ (anganavaadi kaaryakarte); ಅಂಗನವಾಡಿ ಟೀಚರ್ (anganavaadi teacher),anganwadi; angan wadi; aanganbadi; AWW; double u
Anganwadi centre,आंगनवाड़ी केंद्र (aanganwaadi kendra),ಅಂಗನವಾಡಿ ಕೇಂದ್ರ (anganavaadi kendra),anganwadi kendra; AWC
CHO,सी एच ओ (si ech o); कम्युनिटी हेल्थ ऑफिसर,ಸಿ ಎಚ್ ಒ (si ech o),c h o; see ech o; cheo
Medical Officer,डॉक्टर साहब (doctor saahab); एम ओ (em o),ಡಾಕ್ಟರ್ (daaktar); ವೈದ್ಯಾಧಿಕಾರಿ (vaidyaadhikaari),MO; em o; daktar
PHC,पी एच सी (pi ech si); सरकारी अस्पताल (sarkaari aspataal),ಪಿ ಎಚ್ ಸಿ (pi ech si); ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರ (praathamika aarogya kendra),p h c; pee aich see; PSC; BHC
CHC,सी एच सी (si ech si),ಸಿ ಎಚ್ ಸಿ (si ech si); ಸಮುದಾಯ ಆರೋಗ್ಯ ಕೇಂದ್ರ (samudaaya aarogya kendra),c h c; see aich see; CHC hospital; PHC (confusion)
Sub-centre,उपकेंद्र (upkendra); सब सेंटर (sub center),ಉಪಕೇಂದ್ರ (upakendra); ಸಬ್ ಸೆಂಟರ್ (sab center),sub center; subcentre; sab sentar
Ayushman Arogya Mandir (HWC),आयुष्मान आरोग्य मंदिर (aayushmaan aarogya mandir); वेलनेस सेंटर (wellness center),ಆಯುಷ್ಮಾನ್ ಆರೋಗ್ಯ ಮಂದಿರ (aayushmaan aarogya mandira); ಹೆಲ್ತ್ ವೆಲ್ನೆಸ್ ಸೆಂಟರ್,HWC; h w c; wellness centre; aarogya mandir
District hospital,जिला अस्पताल (zila aspataal),ಜಿಲ್ಲಾ ಆಸ್ಪತ್ರೆ (jillaa aaspatre),zila hospital; jilla aspatre; DH
Taluk hospital,तालुका अस्पताल (taaluka aspataal),ತಾಲ್ಲೂಕು ಆಸ್ಪತ್ರೆ (taallooku aaspatre),taluk aspatre; taluka hospital; TH
FRU,एफ आर यू (ef aar yu),ಎಫ್ ಆರ್ ಯು (ef aar yu),f r u; first referral unit; efaru
SNCU,एस एन सी यू (es en si yu),ಎಸ್ ಎನ್ ಸಿ ಯು (es en si yu),s n c u; NICU (confusion); snaku
NRC,एन आर सी (en aar si); पोषण पुनर्वास केंद्र (poshan punarvaas kendra),ಎನ್ ಆರ್ ಸಿ (en aar si); ಪೌಷ್ಟಿಕ ಪುನರ್ವಸತಿ ಕೇಂದ್ರ,n r c; NRC centre; enarsi
108 ambulance,एक सौ आठ (ek sau aath); एम्बुलेंस (ambulance),ನೂರ ಎಂಟು (noora entu); ಆಂಬುಲೆನ್ಸ್ (aambulens),one zero eight; ek shunya aath; 180; ambulance gaadi
102 ambulance,एक सौ दो (ek sau do); जननी एक्सप्रेस (janani express),ನೂರ ಎರಡು (noora eradu); ನಗು ಮಗು (nagu magu - UNVERIFIED Karnataka name),one zero two; 120; nagu magu
ANC,ए एन सी (e en si); जांच (jaanch); गर्भ जांच (garbh jaanch),ಎ ಎನ್ ಸಿ (e en si); ಗರ್ಭಿಣಿ ತಪಾಸಣೆ (garbhini tapaasane),a n c; and see; ancy; NC; एनसी; ANC checkup
ANC registration,नाम लिखवाना (naam likhwaana); रजिस्ट्रेशन (registration),ನೋಂದಣಿ (nondani); ರಿಜಿಸ್ಟ್ರೇಷನ್ (rijistreshan),registration; register karna; nondani
First ANC visit,पहली जांच (pehli jaanch),ಮೊದಲ ತಪಾಸಣೆ (modala tapaasane),first checkup; pehla ANC; 1st ANC
Fourth ANC visit,चौथी जांच (chauthi jaanch),ನಾಲ್ಕನೇ ತಪಾಸಣೆ (naalkane tapaasane),4th ANC; four ANC; ANC 4
PNC,पी एन सी (pi en si); प्रसव के बाद जांच (prasav ke baad jaanch),ಪಿ ಎನ್ ಸಿ (pi en si); ಬಾಣಂತಿ ತಪಾಸಣೆ (baananti tapaasane),p n c; pee and see; BNC; penci
HBNC,एच बी एन सी (ech bi en si); नवजात गृह भ्रमण (navjaat grih bhraman),ಎಚ್ ಬಿ ಎನ್ ಸಿ (ech bi en si); ಮನೆ ಭೇಟಿ (mane bheti),h b n c; HPNC; HBNC visit; aich bee en see
HBYC,एच बी वाई सी (ech bi vaai si),ಎಚ್ ಬಿ ವೈ ಸಿ (ech bi vai si),h b y c; HBNC (confusion); HPYC; aich bee why see
Home visit,घर भेंट (ghar bhent); विज़िट (visit),ಮನೆ ಭೇಟಿ (mane bheti); ವಿಸಿಟ್ (visit),visit; gruha bheti; ghar visit
JSY,जे एस वाई (je es vaai); जननी सुरक्षा योजना (janani suraksha yojana),ಜೆ ಎಸ್ ವೈ (je es vai); ಜನನಿ ಸುರಕ್ಷಾ ಯೋಜನೆ (janani surakshaa yojane),j s y; JSI; janani suraksha; jay es why
JSSK,जे एस एस के (je es es ke); जननी शिशु सुरक्षा कार्यक्रम,ಜೆ ಎಸ್ ಎಸ್ ಕೆ (je es es ke),j s s k; JSK; janani shishu
PMSMA,पी एम एस एम ए (pi em es em e); नौ तारीख वाली जांच (nau taareekh waali jaanch),ಪಿ ಎಂ ಎಸ್ ಎಂ ಎ (pi em es em e); ಒಂಬತ್ತನೇ ತಾರೀಖು ತಪಾಸಣೆ (ombattane taareekhu tapaasane),p m s m a; PMSM; pradhan mantri surakshit matritva; 9 tareekh
PMMVY,पी एम एम वी वाई (pi em em vi vaai); मातृ वंदना (maatru vandana),ಪಿ ಎಂ ಎಂ ವಿ ವೈ; ಮಾತೃ ವಂದನಾ (maatru vandanaa),p m m v y; matru vandana; matra vandana
Thayi card,थायी कार्ड (thaayi card),ತಾಯಿ ಕಾರ್ಡ್ (taayi kaard),tai card; thai card; tayi kaard; die card
MCP card,एम सी पी कार्ड (em si pi card); जच्चा बच्चा कार्ड (jachcha bachcha card); टीका कार्ड (teeka card),ಎಂ ಸಿ ಪಿ ಕಾರ್ಡ್ (em si pi kaard); ತಾಯಿ ಕಾರ್ಡ್ (taayi kaard),m c p card; MCB card; NCP card; empty card; m c p
Madilu kit,मडिलु किट (madilu kit),ಮಡಿಲು ಕಿಟ್ (madilu kit),madlu kit; maddilu; medulu kit; madilu
Prasooti Araike,प्रसूति आरैके (prasooti aaraike),ಪ್ರಸೂತಿ ಆರೈಕೆ (prasooti aaraike),prasuti araike; prasuthi aaraike; prasooti araika
Thayi Bhagya,थायी भाग्य (thaayi bhaagya),ತಾಯಿ ಭಾಗ್ಯ (taayi bhaagya),tai bhagya; thai bhagya
RCH ID,आर सी एच आई डी (aar si ech aai di); आर सी एच नंबर,ಆರ್ ಸಿ ಎಚ್ ಐಡಿ (aar si ech ai di),r c h id; RCH number; arch id; RC hid
RCH register,आर सी एच रजिस्टर (aar si ech register),ಆರ್ ಸಿ ಎಚ್ ರಿಜಿಸ್ಟರ್,r c h register; RCH portal
ASHA diary,आशा डायरी (aasha diary),ಆಶಾ ಡೈರಿ (aasha dairy),asha dairy; aasha diary
Survey register,सर्वे रजिस्टर (survey register),ಸರ್ವೆ ರಿಜಿಸ್ಟರ್ (sarve rijistar),servey; sarve register
Eligible couple register,योग्य दंपति रजिस्टर (yogya dampati register); ई सी रजिस्टर (EC register),ಅರ್ಹ ದಂಪತಿ ರಿಜಿಸ್ಟರ್ (arha dampati rijistar),EC register; e c; eligible couple; easy register
Due list,ड्यू लिस्ट (due list),ಡ್ಯೂ ಲಿಸ್ಟ್ (dyoo list),due list; do list; dew list; duelist
Village health register,ग्राम स्वास्थ्य रजिस्टर (graam swaasthya register),ಗ್ರಾಮ ಆರೋಗ್ಯ ರಿಜಿಸ್ಟರ್ (graama aarogya rijistar),VHR; village register
ABHA ID,आभा आई डी (aabha ID); आभा कार्ड (aabha card),ಆಭಾ ಐಡಿ (aabhaa ai di); ಆಭಾ ಕಾರ್ಡ್,abha; aabha; ABHA number; aaba; ABA card
Aadhaar,आधार (aadhaar); आधार कार्ड,ಆಧಾರ್ (aadhaar); ಆಧಾರ್ ಕಾರ್ಡ್,adhar; aadhar; adar card
Ayushman card,आयुष्मान कार्ड (aayushmaan card),ಆಯುಷ್ಮಾನ್ ಕಾರ್ಡ್ (aayushmaan kaard),ayushman; PMJAY card; ayushmaan bharat card
U-WIN,यू विन (yu win),ಯು ವಿನ್ (yu vin),u win; you win; uwin; U-WIN app
Mobile number,मोबाइल नंबर (mobile number); फ़ोन नंबर,ಮೊಬೈಲ್ ನಂಬರ್ (mobail nambar); ಫೋನ್ ನಂಬರ್,mobile; number; phone no
Bank account,बैंक खाता (bank khaata); पासबुक (passbook),ಬ್ಯಾಂಕ್ ಖಾತೆ (byaank khaate); ಪಾಸ್ ಬುಕ್,khata; account number; passbook
Incentive,प्रोत्साहन राशि (protsaahan raashi); इंसेंटिव (incentive); पैसा (paisa),ಪ್ರೋತ್ಸಾಹ ಧನ (protsaaha dhana); ಇನ್ಸೆಂಟಿವ್ (insentiv),incentive; insentive; protsahan
LMP,एल एम पी (el em pi); आखिरी माहवारी (aakhiri maahvaari); पिछला महीना (pichhla mahina),ಎಲ್ ಎಂ ಪಿ (el em pi); ಕೊನೆಯ ಮುಟ್ಟು (koneya muttu),l m p; elampee; last period; MP
EDD,ई डी डी (i di di); डिलीवरी की तारीख (delivery ki taareekh),ಇ ಡಿ ಡಿ (i di di); ಹೆರಿಗೆ ದಿನಾಂಕ (herige dinaanka),e d d; EDT; due date; ED D
Pregnancy,गर्भ (garbh); पेट से (pet se); उम्मीद से (ummeed se),ಗರ್ಭ (garbha); ಬಸುರಿ (basuri),pregnant; garbhavati; pet se hai; basuri
Pregnant woman,गर्भवती (garbhvati),ಗರ್ಭಿಣಿ (garbhini); ಬಸುರಿ (basuri),garbhavati; garbhini; pregnant lady
Postpartum mother,प्रसूता (prasoota); जच्चा (jachcha),ಬಾಣಂತಿ (baananti),baanthi; bananthi; jacha; prasuta
Newborn,नवजात (navjaat); बच्चा (bachcha),ನವಜಾತ ಶಿಶು (navajaata shishu); ಮಗು (magu),navjat; new born; nawajaat; magu
Gravida (number of pregnancy),कौन सा बच्चा (kaun sa bachcha); पहला / दूसरा गर्भ,ಎಷ್ಟನೇ ಗರ್ಭ (eshtane garbha); ಮೊದಲ ಬಸುರಿ,G1; G2; first pregnancy; gravida; primi
Primi,पहला बच्चा (pehla bachcha); प्राइमी (primi),ಚೊಚ್ಚಲ ಹೆರಿಗೆ (chochchala herige),primi; premie (confusion with preterm); chochalu
Trimester,तिमाही (timaahi); तीन महीने (teen mahine),ತ್ರೈಮಾಸಿಕ (traimaasika); ಮೂರು ತಿಂಗಳು (mooru tingalu),trimester; tri mester; timahi
High risk pregnancy (HRP),हाई रिस्क (high risk); खतरे वाली गर्भावस्था,ಹೈ ರಿಸ್ಕ್ (hai risk); ಅಪಾಯಕಾರಿ ಗರ್ಭ (apaayakaari garbha),HRP; h r p; high risk; hirisk
Danger signs,खतरे के लक्षण (khatre ke lakshan),ಅಪಾಯದ ಲಕ್ಷಣಗಳು (apaayada lakshanagalu),danger sign; khatra; apaya
Referral,रेफर (refer); बड़े अस्पताल भेजना (bade aspataal bhejna),ರೆಫರ್ (refar); ಕಳುಹಿಸು (kaluhisu),refer; referal; reefer
Institutional delivery,अस्पताल में डिलीवरी (aspataal mein delivery); संस्थागत प्रसव (sansthaagat prasav),ಆಸ್ಪತ್ರೆ ಹೆರಿಗೆ (aaspatre herige); ಸಾಂಸ್ಥಿಕ ಹೆರಿಗೆ (saansthika herige),hospital delivery; institution delivery; sansthagat
Home delivery,घर पर डिलीवरी (ghar par delivery); घर पर प्रसव,ಮನೆ ಹೆರಿಗೆ (mane herige),home delivery; ghar delivery; mane herige
Delivery,डिलीवरी (delivery); प्रसव (prasav); जचगी (jachgi),ಹೆರಿಗೆ (herige); ಡೆಲಿವರಿ (delivari),delivery; dilivery; prasav; herige
Normal delivery,नॉर्मल (normal); सामान्य प्रसव,ನಾರ್ಮಲ್ ಹೆರಿಗೆ (naarmal herige); ಸಹಜ ಹೆರಿಗೆ (sahaja herige),normal; normel; NVD
Caesarean,ऑपरेशन (operation); सिजेरियन (cesarean); बड़ा ऑपरेशन,ಆಪರೇಷನ್ (aapareshan); ಸಿಸೇರಿಯನ್ (sizeriyan),operation; C-section; LSCS; sizerian; seezer
Abortion,गर्भपात (garbhpaat); बच्चा गिरना (bachcha girna); सफाई (safaai),ಗರ್ಭಪಾತ (garbhapaata); ಅಬಾರ್ಷನ್ (abaarshan),abortion; MTP; garbhapat; miscarriage
Stillbirth,मरा हुआ बच्चा (mara hua bachcha); मृत जन्म (mrit janm),ಸತ್ತು ಹುಟ್ಟಿದ ಮಗು (sattu huttida magu),stillbirth; still born; IUD (confusion)
Twins,जुड़वां (judwaan),ಅವಳಿ (avali); ಜೋಡಿ ಮಕ್ಕಳು (jodi makkalu),twins; judva; avali
Low birth weight,कम वज़न (kam vazan); कमजोर बच्चा (kamzor bachcha),ಕಡಿಮೆ ತೂಕದ ಮಗು (kadime tookada magu),LBW; l b w; low weight; kam wajan
Preterm,समय से पहले (samay se pehle); अधूरे महीने (adhoore mahine),ಅವಧಿ ಪೂರ್ವ (avadhi poorva); ತಿಂಗಳು ತುಂಬದ ಮಗು (tingalu tumbada magu),premature; preterm; pre term; premi
Kangaroo mother care,कंगारू मदर केयर (KMC); छाती से लगाना,ಕಾಂಗರೂ ಆರೈಕೆ (kaangaroo aaraike),KMC; k m c; kangaru; kangroo care
Breastfeeding,स्तनपान (stanpaan); दूध पिलाना (doodh pilaana),ಎದೆಹಾಲು ಕುಡಿಸುವುದು (edehaalu kudisuvudu); ಮೊಲೆ ಹಾಲು,breast feeding; stanpan; ede haalu
Exclusive breastfeeding,केवल स्तनपान (keval stanpaan); सिर्फ माँ का दूध,ಕೇವಲ ಎದೆಹಾಲು (kevala edehaalu),exclusive; only breast milk; six months breastfeeding
Colostrum,पहला दूध (pehla doodh); पीला गाढ़ा दूध (peela gaadha doodh),ಗಿಣ್ಣು ಹಾಲು (ginnu haalu); ಮೊದಲ ಹಾಲು (modala haalu),colostrum; kolostrum; ginnu
Complementary feeding,ऊपरी आहार (oopari aahaar); अन्नप्राशन (annapraashan),ಪೂರಕ ಆಹಾರ (pooraka aahaara); ಅನ್ನಪ್ರಾಶನ,complementary food; annaprashan; upari khana
Umbilical cord,नाल (naal); नाभि (naabhi),ಹೊಕ್ಕುಳು (hokkulu); ಹೊಕ್ಕುಳ ಬಳ್ಳಿ (hokkula balli),naal; nabhi; cord; hokkalu
Hypothermia,ठंडा पड़ना (thanda padna),ಮೈ ತಣ್ಣಗಾಗುವುದು (mai tannagaaguvudu),cold baby; thanda; hypothermia
Jaundice,पीलिया (peeliya),ಕಾಮಾಲೆ (kaamaale); ಹಳದಿ (haladi),piliya; jondis; kamale
Fever,बुखार (bukhaar); ताप (taap),ಜ್ವರ (jvara),bukhar; jwara; fiver
Diarrhoea,दस्त (dast); पतले दस्त (patle dast); लूज़ मोशन (loose motion),ಭೇದಿ (bhedi); ಅತಿಸಾರ (atisaara),loose motion; dast; bedi; diarrhea
Pneumonia,निमोनिया (nimoniya); सांस तेज़ (saans tez),ನ್ಯುಮೋನಿಯಾ (nyumoniyaa),nimonia; numonia; fast breathing
Convulsions,झटके (jhatke); दौरा (daura); मिर्गी (mirgi),ಫಿಟ್ಸ್ (fits); ಸೆಳೆತ (selata),fits; jhatka; seizure; selatha
Bleeding,खून आना (khoon aana); रक्तस्राव (raktasraav),ರಕ್ತಸ್ರಾವ (raktasraava); ರಕ್ತ ಹೋಗುವುದು (rakta hoguvudu),bleeding; khoon; rakta; PPH
Swelling,सूजन (soojan),ಊತ (oota); ಬಾವು (baavu),sujan; soojan; oota; edema
Headache,सिर दर्द (sir dard),ತಲೆ ನೋವು (tale novu),sar dard; tale novu
Blurred vision,धुंधला दिखना (dhundhla dikhna),ಮಸುಕು ಕಣ್ಣು (masuku kannu),dhundhla; blur
Anaemia,खून की कमी (khoon ki kami); एनीमिया (anemia),ರಕ್ತಹೀನತೆ (raktaheenate); ಅನೀಮಿಯಾ,anemia; anaemia; khoon kam; rakta kadime
Malnutrition (SAM/MAM),कुपोषण (kuposhan); सैम (SAM); मैम (MAM),ಅಪೌಷ್ಟಿಕತೆ (apaushtikate); ಸ್ಯಾಮ್ (SAM),SAM; MAM; same; mam; kuposhan
Growth chart,वृद्धि चार्ट (vriddhi chart); ग्रोथ चार्ट,ಬೆಳವಣಿಗೆ ಚಾರ್ಟ್ (belavanige chaart),growth chart; grows chart; WFA
Weight,वज़न (vazan),ತೂಕ (tooka),wajan; vajan; tooka; wait
Height,लंबाई (lambaai); ऊंचाई (oonchaai),ಎತ್ತರ (ettara); ಉದ್ದ (udda),length; height; lambai; ettara
MUAC,मुआक (muaak); बांह का नाप (baanh ka naap),ಮುವಾಕ್ (muvaak); ತೋಳಿನ ಸುತ್ತಳತೆ (tolina suttalate),muac; mu ack; m u a c; MUAC tape
Weighing scale,वज़न मशीन (vazan machine); तराज़ू (taraazu),ತೂಕದ ಯಂತ್ರ (tookada yantra); ವೇಯಿಂಗ್ ಮೆಷಿನ್,weighing machine; scale; tarazu
Thermometer,थर्मामीटर (tharmaameetar),ಥರ್ಮಾಮೀಟರ್ (tharmaameetar),thermameter; tharmometer
Temperature,तापमान (taapmaan); टेम्परेचर,ಉಷ್ಣಾಂಶ (ushnaamsha); ಟೆಂಪರೇಚರ್,temp; temprature; degree
Hb,एच बी (ech bi); हीमोग्लोबिन (heemoglobin); खून की जांच (khoon ki jaanch),ಎಚ್ ಬಿ (ech bi); ಹಿಮೋಗ್ಲೋಬಿನ್ (himoglobin),h b; HP; HB level; aich bee; hemoglobin; himoglobin
BP,बी पी (bi pi); ब्लड प्रेशर (blood pressure),ಬಿ ಪಿ (bi pi); ರಕ್ತದೊತ್ತಡ (raktadottada),b p; bee pee; BB; VP; blood pressure
Blood sugar,शुगर (sugar); खून में शक्कर,ಶುಗರ್ (shugar); ಸಕ್ಕರೆ ಕಾಯಿಲೆ (sakkare kaayile),sugar; GRBS; RBS; shugar
GDM test (OGTT),शुगर टेस्ट (sugar test); ग्लूकोज़ पीकर जांच,ಶುಗರ್ ಟೆಸ್ಟ್; ಗ್ಲುಕೋಸ್ ಟೆಸ್ಟ್,GDM; g d m; OGTT; o g t t; glucose test
Urine test,पेशाब की जांच (peshaab ki jaanch); यूरिन टेस्ट,ಮೂತ್ರ ಪರೀಕ್ಷೆ (mootra pareekshe),urine; peshab; albumin; urine sugar
Urine albumin,एल्ब्यूमिन (albumin),ಆಲ್ಬುಮಿನ್ (aalbumin),albumin; album in; albumen
Pregnancy test kit,निश्चय किट (nishchay kit); प्रेगनेंसी टेस्ट,ನಿಶ್ಚಯ್ ಕಿಟ್ (nishchay kit); ಪ್ರೆಗ್ನೆನ್ಸಿ ಕಿಟ್,nischay; nishchay; UPT; pregnancy kit
HIV test,एच आई वी टेस्ट (ech aai vi test),ಎಚ್ ಐ ವಿ ಪರೀಕ್ಷೆ (ech ai vi pareekshe),h i v; HIB; aich i v
Syphilis test (VDRL),वी डी आर एल (vi di aar el),ವಿ ಡಿ ಆರ್ ಎಲ್ (vi di aar el),VDRL; v d r l; RPR; syphilis
Blood group,ब्लड ग्रुप (blood group),ಬ್ಲಡ್ ಗ್ರೂಪ್ (blad groop); ರಕ್ತದ ಗುಂಪು,blood group; blad group
HBsAg,हेपेटाइटिस बी टेस्ट (hepatitis B test),ಹೆಪಟೈಟಿಸ್ ಬಿ ಪರೀಕ್ಷೆ,HBsAg; h b s a g; hep B test
Ultrasound,अल्ट्रासाउंड (ultrasound); सोनोग्राफी (sonography),ಸ್ಕ್ಯಾನಿಂಗ್ (skyaaning); ಅಲ್ಟ್ರಾಸೌಂಡ್,scan; scanning; USG; u s g; sonography
Fetal heart sound,बच्चे की धड़कन (bachche ki dhadkan),ಮಗುವಿನ ಎದೆ ಬಡಿತ (maguvina ede badita),FHS; f h s; heartbeat; dhadkan
Fetal movement,बच्चे का हिलना (bachche ka hilna),ಮಗುವಿನ ಚಲನೆ (maguvina chalane),baby movement; hilna; chalane
RDT (malaria),आर डी टी (aar di ti); मलेरिया टेस्ट,ಆರ್ ಡಿ ಟಿ (aar di ti); ಮಲೇರಿಯಾ ಪರೀಕ್ಷೆ,RDT; r d t; ardt; malaria kit
Sputum test,बलगम की जांच (balgam ki jaanch),ಕಫ ಪರೀಕ್ಷೆ (kapha pareekshe),balgam; sputum; kapha; cough test
Immunization,टीकाकरण (teekaakaran); टीका (teeka); सुई (sui),ಲಸಿಕೆ (lasike); ಚುಚ್ಚುಮದ್ದು (chuchchumaddu),tika; teeka; vaccine; lasike; injection
Vaccination session,टीका दिवस (teeka diwas); टीके का दिन,ಲಸಿಕೆ ದಿನ (lasike dina),session; tika day; VHND
VHND,वी एच एन डी (vi ech en di); ग्राम स्वास्थ्य पोषण दिवस,ವಿ ಎಚ್ ಎನ್ ಡಿ (vi ech en di),v h n d; VHSND; village health day
VHSNC,वी एच एस एन सी (vi ech es en si); ग्राम स्वास्थ्य समिति,ವಿ ಎಚ್ ಎಸ್ ಎನ್ ಸಿ; ಗ್ರಾಮ ಆರೋಗ್ಯ ಸಮಿತಿ,v h s n c; VHSC; samiti meeting
UIP,यू आई पी (yu aai pi); सरकारी टीकाकरण,ಯು ಐ ಪಿ (yu ai pi),u i p; universal immunization
Mission Indradhanush,मिशन इंद्रधनुष (mission indradhanush),ಮಿಷನ್ ಇಂದ್ರಧನುಷ್ (mishan indradhanush),indradhanush; indra dhanush; IMI
Pulse Polio,पल्स पोलियो (pulse polio); पोलियो रविवार,ಪಲ್ಸ್ ಪೋಲಿಯೋ (pals poliyo),pulse polio; palse polio; polio drop
Zero dose,ज़ीरो डोज़ (zero dose); जन्म का टीका,ಶೂನ್ಯ ಡೋಸ್ (shoonya dos); ಜೀರೋ ಡೋಸ್,zero dose; 0 dose; birth dose
Birth dose,जन्म का टीका (janm ka teeka),ಜನನ ಡೋಸ್ (janana dos); ಹುಟ್ಟಿದಾಗ ಲಸಿಕೆ,birth dose; berth dose
Booster,बूस्टर (booster),ಬೂಸ್ಟರ್ (boostar),booster; buster; boost
BCG,बी सी जी (bi si ji); बाएं हाथ का टीका (baayen haath ka teeka),ಬಿ ಸಿ ಜಿ (bi si ji),b c g; BCZ; PCG; BCD; bee see jee
BCG scar,बी सी जी का निशान (BCG ka nishaan),ಬಿ ಸಿ ಜಿ ಗುರುತು (BCG gurutu),BCG mark; scar; nishan
OPV,ओ पी वी (o pi vi); पोलियो की दवा (polio ki dava); पोलियो ड्रॉप,ಒ ಪಿ ವಿ (o pi vi); ಪೋಲಿಯೋ ಹನಿ (poliyo hani),o p v; OPB; OBV; polio drops; ओपीवी
bOPV,बी ओ पी वी (bi o pi vi),ಬಿ ಒ ಪಿ ವಿ,b o p v; BOPV; bivalent
Hepatitis B,हेपेटाइटिस बी (hepatitis B); हेप बी,ಹೆಪಟೈಟಿಸ್ ಬಿ (hepataitis bi),hep B; hepatitis; hepa B; Hep-B
Pentavalent,पेंटा (penta); पेंटावेलेंट (pentavalent),ಪೆಂಟಾ (pentaa); ಪೆಂಟಾವೆಲೆಂಟ್ (pentaavelent),penta; pentavalent; penta valent; pentavelant; Penta 1
Rotavirus vaccine (RVV),रोटा (rota); रोटावायरस (rotavirus),ರೋಟಾ (rotaa); ರೋಟಾವೈರಸ್,RVV; r v v; rota; roti virus; rota drops
fIPV,एफ आई पी वी (ef aai pi vi); आई पी वी,ಎಫ್ ಐ ಪಿ ವಿ (ef ai pi vi),f i p v; IPV; FIPV; fipv; if IPV
PCV,पी सी वी (pi si vi); न्यूमोकोकल,ಪಿ ಸಿ ವಿ (pi si vi),p c v; PCB; BCV; pneumococcal
MR,एम आर (em aar); खसरा रूबेला (khasra rubella); खसरे का टीका,ಎಂ ಆರ್ (em aar); ದಡಾರ ರುಬೆಲ್ಲಾ (dadaara rubella),m r; MR 1; MR 2; emar; mister (confusion); measles
Measles,खसरा (khasra); छोटी माता (chhoti maata - UNSOURCED),ದಡಾರ (dadaara); ದಡಾರ ಲಸಿಕೆ,khasra; measle; dadara
JE vaccine,जे ई (je i); दिमागी बुखार का टीका (dimaagi bukhaar ka teeka),ಜೆ ಇ (je i); ಮೆದುಳು ಜ್ವರ ಲಸಿಕೆ (medulu jvara lasike),j e; GE; JEE; je ee; Japanese encephalitis
DPT,डी पी टी (di pi ti); त्रिगुणी टीका (triguni teeka),ಡಿ ಪಿ ಟಿ (di pi ti),d p t; DPD; BPT; DTP; DPT booster
Td,टी डी (ti di); टिटनेस का टीका (titnes ka teeka),ಟಿ ಡಿ (ti di); ಟಿಡಿ ಲಸಿಕೆ,t d; TD; teedee; TT (older name); Td 1; Td 2
TT (older name for Td),टी टी (ti ti); टिटनेस (titnes); टिटनस,ಟಿ ಟಿ (ti ti); ಟಿಟಿ ಇಂಜೆಕ್ಷನ್,titi; tee tee; T T; tetanus; titanus; TT injection
Td booster,टी डी बूस्टर (Td booster),ಟಿ ಡಿ ಬೂಸ್ಟರ್ (Td boostar),TD booster; TT booster; tee dee booster
Vitamin A,विटामिन ए (vitamin e); विटामिन ए की खुराक,ವಿಟಮಿನ್ ಎ (vitamin e),vitamin A; vitamin E (confusion); vit A; vitamin ay
HPV vaccine,एच पी वी (ech pi vi),ಎಚ್ ಪಿ ವಿ (ech pi vi),h p v; HBV (confusion); HPB; cervical vaccine
AEFI,ए ई एफ आई (e i ef aai); टीके के बाद बुखार,ಎ ಇ ಎಫ್ ಐ,a e f i; AFI; side effect
Vaccine carrier,वैक्सीन कैरियर (vaccine carrier),ವ್ಯಾಕ್ಸಿನ್ ಕ್ಯಾರಿಯರ್,carrier; vaccine box
IFA,आई एफ ए (aai ef e); आयरन की गोली (iron ki goli),ಐ ಎಫ್ ಎ (ai ef e); ಕಬ್ಬಿಣಾಂಶದ ಮಾತ್ರೆ (kabbinaamshada maatre),aayefe; i f a; IFE; ifa; aai fa; iron folic
Red IFA tablet,लाल गोली (laal goli); खून की गोली (khoon ki goli); आयरन गोली,ಕೆಂಪು ಮಾತ್ರೆ (kempu maatre); ಕಬ್ಬಿಣದ ಮಾತ್ರೆ (kabbinada maatre),lal goli; laal goli; red tablet; kempu matre; khoon goli
Blue IFA tablet,नीली गोली (neeli goli),ನೀಲಿ ಮಾತ್ರೆ (neeli maatre),blue tablet; neeli goli; WIFS
Pink IFA tablet,गुलाबी गोली (gulaabi goli),ಗುಲಾಬಿ ಮಾತ್ರೆ (gulaabi maatre),pink tablet; gulabi goli
IFA syrup,आयरन सिरप (iron syrup),ಐರನ್ ಸಿರಪ್ (airan sirap),iron syrup; IFA syrup; siroop
Folic acid,फोलिक एसिड (folic acid),ಫೋಲಿಕ್ ಆಸಿಡ್ (folik aasid),folic; follic; folik acid
Calcium,कैल्शियम (calcium); सफेद गोली (safed goli - UNVERIFIED),ಕ್ಯಾಲ್ಸಿಯಂ (kyaalsiyam); ಬಿಳಿ ಮಾತ್ರೆ (bili maatre - UNVERIFIED),calcium; kalsium; calsium; kelshiyam
Albendazole,एल्बेंडाज़ोल (albendazole); पेट के कीड़े की गोली (pet ke keede ki goli),ಆಲ್ಬೆಂಡಜೋಲ್ (aalbendajol); ಜಂತುಹುಳು ಮಾತ್ರೆ (jantuhulu maatre),albendazol; albenda; albendajole; kide ki goli; jantu hula
Deworming,कृमि मुक्ति (krimi mukti); पेट के कीड़े निकालना,ಜಂತುಹುಳು ನಿವಾರಣೆ (jantuhulu nivaarane),deworming; NDD; krimi; jantuhulu
ORS,ओ आर एस (o aar es); घोल (ghol); जीवन रक्षक घोल,ಒ ಆರ್ ಎಸ್ (o aar es); ಒ ಆರ್ ಎಸ್ ದ್ರಾವಣ (o aar es draavana),o r s; oars; ORS packet; or yes; OIRS
Zinc,जिंक (zinc); जिंक की गोली,ಜಿಂಕ್ (jink); ಜಿಂಕ್ ಮಾತ್ರೆ,zink; jink; sink; zing
Paracetamol,पैरासिटामोल (paracetamol); बुखार की गोली,ಪ್ಯಾರಾಸಿಟಮಾಲ್ (pyaaraasitamaal),paracetamol; PCM; parasitamol; crocin
Cotrimoxazole,कोट्रिमोक्साज़ोल (cotrim),ಕೋಟ್ರಿಮ್ (kotrim),cotrim; co-trimoxazole; cotrimox
Chlorhexidine,क्लोरहेक्सिडिन (chlorhexidine),ಕ್ಲೋರ್ಹೆಕ್ಸಿಡಿನ್,CHX; chlorhex; chlor hexidine
Misoprostol,मिसोप्रोस्टोल (misoprostol),ಮಿಸೋಪ್ರೋಸ್ಟಾಲ್,miso; misoprost; misoprostal
Vitamin K,विटामिन के (vitamin K),ವಿಟಮಿನ್ ಕೆ,vitamin K; vit K; vitamin cake
Iron sucrose,आयरन सुक्रोज़ (iron sucrose); आयरन की बोतल,ಐರನ್ ಸುಕ್ರೋಸ್ (airan sukros),iron sucrose; IV iron; FCM; iron drip
Mala-N,माला एन (mala N); गर्भनिरोधक गोली,ಮಾಲಾ ಎನ್ (maalaa en),mala n; mala; OCP; pill
Chhaya,छाया (chhaaya); हफ्ते वाली गोली (hafte waali goli),ಛಾಯಾ (chhaayaa),chaya; chhaya; centchroman; saheli
Antara,अंतरा (antara); तीन महीने का इंजेक्शन,ಅಂತರ (antara); ಅಂತರ ಇಂಜೆಕ್ಷನ್,antara; DMPA; antra injection
Condom,निरोध (nirodh); कंडोम (condom),ಕಾಂಡೋಮ್ (kaandom); ನಿರೋಧ್,nirodh; condom; kandom
Copper T (IUCD),कॉपर टी (copper T); छल्ला (chhalla),ಕಾಪರ್ ಟಿ (kaapar ti),copper T; IUCD; PPIUCD; copper tee; chhalla
Emergency contraceptive pill,इमरजेंसी गोली (emergency goli); ई सी पी,ಇ ಸಿ ಪಿ; ತುರ್ತು ಗರ್ಭನಿರೋಧಕ ಮಾತ್ರೆ,ECP; e c p; i-pill
Sterilization,नसबंदी (nasbandi); ऑपरेशन (operation),ಸಂತಾನಹರಣ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆ (santaanaharana); ಕುಟುಂಬ ಯೋಜನೆ ಆಪರೇಷನ್,nasbandi; tubectomy; vasectomy; family planning operation
Family planning,परिवार नियोजन (parivaar niyojan),ಕುಟುಂಬ ಕಲ್ಯಾಣ (kutumba kalyaana); ಕುಟುಂಬ ಯೋಜನೆ (kutumba yojane),FP; family planning; parivar niyojan
Sanitary napkin,सेनेटरी पैड (sanitary pad),ಸ್ಯಾನಿಟರಿ ಪ್ಯಾಡ್,pad; napkin; sanitary
Iodized salt,आयोडीन नमक (iodine namak),ಅಯೋಡಿನ್ ಉಪ್ಪು (ayodin uppu),iodine salt; iodized
RBSK,आर बी एस के (aar bi es ke),ಆರ್ ಬಿ ಎಸ್ ಕೆ (aar bi es ke),r b s k; RBSK team; RBC
RKSK,आर के एस के (aar ke es ke); किशोर स्वास्थ्य,ಆರ್ ಕೆ ಎಸ್ ಕೆ,r k s k; adolescent health
Anemia Mukt Bharat,एनीमिया मुक्त भारत (anemia mukt bhaarat),ಅನೀಮಿಯಾ ಮುಕ್ತ ಭಾರತ,AMB; anemia mukt; anaemia mukth
MAA programme,माँ कार्यक्रम (maa) - स्तनपान,ಮಾ (maa) ಕಾರ್ಯಕ್ರಮ,MAA; mothers absolute affection
SAANS,सांस अभियान (saans),ಸಾನ್ಸ್ (saans),saans; SAANS campaign; sans
IDCF (diarrhoea fortnight),दस्त पखवाड़ा (dast pakhwaada),ಅತಿಸಾರ ಪಾಕ್ಷಿಕ (atisaara paakshika),IDCF; STOP diarrhoea; dast pakhwada
Poshan Abhiyaan,पोषण अभियान (poshan abhiyaan),ಪೋಷಣ ಅಭಿಯಾನ (poshana abhiyaana),poshan; poshan maah; poshan tracker
Take Home Ration,टी एच आर (THR); राशन (raashan),ಟಿ ಎಚ್ ಆರ್; ಪೂರಕ ಪೌಷ್ಟಿಕ ಆಹಾರ,THR; take home; ration
TB,टी बी (ti bi); क्षय रोग (kshay rog),ಟಿ ಬಿ (ti bi); ಕ್ಷಯ (kshaya),t b; TV (confusion); tibi; kshay
Nikshay,निक्षय (nikshay); निक्षय पोषण योजना,ನಿಕ್ಷಯ್ (nikshay),nikshay; nikshay poshan; NPY
DOTS,डॉट्स (dots); टीबी की दवा,ಡಾಟ್ಸ್ (daats),dots; DOT; daily dose
Malaria,मलेरिया (maleriya),ಮಲೇರಿಯಾ (maleriyaa),malaria; maleria; meleria
Dengue,डेंगू (dengu),ಡೆಂಗ್ಯೂ (dengyoo),dengu; dengue; dangue
NCD screening,एन सी डी (en si di); शुगर बीपी जांच,ಎನ್ ಸಿ ಡಿ ತಪಾಸಣೆ,NCD; n c d; CBAC; CBAC form
CBAC form,सी बी ए सी फॉर्म (si bi e si form),ಸಿ ಬಿ ಎ ಸಿ ಫಾರ್ಮ್,CBAC; c b a c; see back
Birth registration,जन्म पंजीकरण (janm panjeekaran); जन्म प्रमाण पत्र,ಜನನ ನೋಂದಣಿ (janana nondani); ಜನನ ಪ್ರಮಾಣಪತ್ರ,birth certificate; janm praman patra
Death,मृत्यु (mrityu); मौत (maut),ಸಾವು (saavu); ಮರಣ (marana),death; maut; saavu; MDR; CDR
Maternal death review (MDR),एम डी आर (em di aar),ಎಂ ಡಿ ಆರ್,MDR; m d r; maternal death
Child death review (CDR),सी डी आर (si di aar),ಸಿ ಡಿ ಆರ್,CDR; c d r; infant death
Dai (traditional birth attendant),दाई (daai),ಸೂಲಗಿತ್ತಿ (soolagitti),dai; daai; soolagitti; TBA
Gestational age in months,महीना (mahina); कितने महीने (kitne mahine),ತಿಂಗಳು (tingalu); ಎಷ್ಟು ತಿಂಗಳು (eshtu tingalu),mahina; tingalu; month
Kilo,किलो (kilo),ಕಿಲೋ (kilo); ಕೆಜಿ (keji),kg; kilo; keji; kilogram
Gram,ग्राम (graam),ಗ್ರಾಂ (graam),gm; gram; graam
Point (decimal),पॉइंट (point); दशमलव (dashamlav),ಪಾಯಿಂಟ್ (paayint); ದಶಮಾಂಶ (dashamaamsha),point; poin; dashamlav
Degree (temperature),डिग्री (digri),ಡಿಗ್ರಿ (digri),degree; digri; F
Tareekh (date),तारीख (taareekh),ತಾರೀಖು (taareekhu); ದಿನಾಂಕ (dinaanka),tarikh; tareek; date; dinanka
Next week,अगले हफ्ते (agle hafte),ಮುಂದಿನ ವಾರ (mundina vaara),agle hapte; mundina vara
Tomorrow,कल (kal),ನಾಳೆ (naale),kal; naale; nale
Yesterday,कल (kal),ನಿನ್ನೆ (ninne),kal; ninne
Day after tomorrow,परसों (parson),ನಾಡಿದ್ದು (naadiddu),parso; parson; naadidu
Day before yesterday,परसों (parson),ಮೊನ್ನೆ (monne),parso; monne
```

Row count: 199 data rows. Notes on specific rows:
- **102 ambulance.** The Karnataka "Nagu Magu" link is UNVERIFIED.
- **Calcium "white tablet".** UNVERIFIED.
- **Measles "chhoti maata".** UNSOURCED. It is also risky, because "chhoti maata" usually means chickenpox.
- **PMSMA "9 tareekh".** This is the 9th-of-month PMSMA day. It is standard NHM nomenclature but was not re-fetched in this pass, so it is UNVERIFIED here.
- **Red IFA tablet and "lal goli".** The red/blue/pink colour coding is sourced to Anemia Mukt Bharat descriptions [S8] (SECONDARY aggregators; the HP NHM page is official). "Lal goli" as the spoken term is UNSOURCED-linguistic.

---

## UIP schedule (reference only; the assistant must NOT compute or advise due dates)

Primary source: *National Immunization Schedule (NIS) for Infants, Children and Pregnant Women*, MoHFW/NHM. This is a PDF on nhm.gov.in with metadata dated 29 May 2020, pages 1 to 3 [S1]. It was cross-checked against the PIB Research Unit factsheet *Celebrating the Power of Vaccines*, 17 March 2026, "National Immunisation Schedule" table, around page 5 to 6 [S2].

| Beneficiary | Vaccine | Dose | When to give | Amount / route |
|---|---|---|---|---|
| Pregnant woman | Td-1 | 1 | Early in pregnancy | 0.5 ml IM, upper arm |
| Pregnant woman | Td-2 | 2 | 4 weeks after Td-1 | 0.5 ml IM, upper arm |
| Pregnant woman | Td-Booster | booster | If 2 TT/Td doses were received in a pregnancy within the last 3 years | 0.5 ml IM, upper arm |
| Infant | BCG | 1 | At birth or as early as possible, until 1 year | 0.1 ml (0.05 ml until 1 month) ID, left upper arm |
| Infant | Hepatitis B birth dose | 0 | At birth or as early as possible within 24 hours | 0.5 ml IM, anterolateral mid-thigh |
| Infant | OPV-0 | 0 | At birth or as early as possible within the first 15 days | 2 drops oral |
| Infant | OPV 1, 2, 3 | 3 | 6, 10 and 14 weeks (can be given until 5 years) | 2 drops oral |
| Infant | Pentavalent 1, 2, 3 | 3 | 6, 10 and 14 weeks (can be given until 1 year) | 0.5 ml IM, anterolateral mid-thigh |
| Infant | Rotavirus (RVV) 1, 2, 3 | 3 | 6, 10 and 14 weeks (until 1 year) | 5 drops (liquid) or 2.5 ml (lyophilised), oral |
| Infant | fIPV 1, 2 | 2 | 6 and 14 weeks | 0.1 ml ID, right upper arm |
| Infant | fIPV 3 | 1 | 9 to 12 months, with MR-1 (**see conflict below**) | 0.1 ml ID |
| Infant | PCV 1, 2 + Booster | 3 | 6 and 14 weeks; booster at 9 to 12 months | 0.5 ml IM, anterolateral mid-thigh |
| Infant | MR-1 | 1 | 9 completed months to 12 months (measles can be given until 5 years) | 0.5 ml SC, right upper arm |
| Infant | JE-1 (endemic districts only) | 1 | 9 completed months to 12 months | 0.5 ml SC, left upper arm (live) or IM thigh (killed) |
| Infant | Vitamin A (1st dose) | 1 | 9 completed months, with MR | 1 ml (1 lakh IU) oral |
| Child | DPT Booster-1 | booster | 16 to 24 months | 0.5 ml IM, anterolateral mid-thigh |
| Child | MR-2 | 2 | 16 to 24 months | 0.5 ml SC, right upper arm |
| Child | OPV Booster | booster | 16 to 24 months | 2 drops oral |
| Child | JE-2 (endemic districts only) | 2 | 16 to 24 months | 0.5 ml |
| Child | Vitamin A (2nd to 9th dose) | 8 | 16 to 18 months, then every 6 months until 5 years | 2 ml (2 lakh IU) oral |
| Child | DPT Booster-2 | booster | 5 to 6 years | 0.5 ml IM, upper arm |
| Adolescent | Td | 2 | 10 years and 16 years | 0.5 ml IM, upper arm |
| Girl, 14 years | HPV | campaign | Nationwide campaign launched 28 February 2026 for 14-year-old girls [S2] | Not stated in source |

Conflicts and caveats:
1. **fIPV-3.** State directives and press reports (Tamil Nadu DPH, Punjab, West Bengal) say a third fIPV dose at 9 to 12 months, given with MR-1, was rolled out nationally from 1 January 2023 [S4] (SECONDARY: news reports of official circulars). The PIB 2026 factsheet table lists only fIPV-1 and fIPV-2 [S2]. **This is unresolved**, so check the current MoHFW NIS or the state RI microplan.
2. **PCV.** The 2020 NHM PDF says PCV is used only in selected states [S1]. The PIB 2026 factsheet lists it without that limitation [S2]. Current national scale-up is therefore implied but not stated explicitly. **Treat it as national per 2026 PIB.**
3. **JE.** Given in endemic districts only [S1][S2]. Whether a given Karnataka district is JE-endemic was **UNVERIFIED** in this pass.
4. **Vitamin A (2nd dose).** The HP NHM page says "at 16 months" [S3]. The NHM NIS PDF says "16 to 18 months" [S1].

---

## Topic 4. Spoken numbers, dates and measurements

All forms in 4a and 4b are **UNSOURCED-linguistic** unless a source is cited. The 0 to 100 tables in 4c are discussed under that heading.

### 4a. Fractions and quantities

**Hindi fractional quantifiers.** These multiply with any unit, including sau (100), hazaar (1000) and kilo.

| Word | Devanagari | Meaning | Examples |
|---|---|---|---|
| paav | पाव | 1/4 | paav kilo = 250 g |
| aadha | आधा | 1/2 | aadha kilo = 500 g |
| paun | पौन | 3/4 | paun kilo = 750 g |
| sava X | सवा | X + 1/4 | sava do = 2.25; sava kilo = 1.25 kg; sava sau = 125 |
| saadhe X | साढ़े | X + 1/2 (used for X ≥ 3) | saadhe teen = 3.5; saadhe nau Hb = 9.5 |
| paune X | पौने | X − 1/4 | paune teen = 2.75; paune do sau = 175 |
| dedh | डेढ़ | 1.5 (replaces "saadhe ek") | dedh kilo; dedh sau = 150; dedh mahina = 1.5 months |
| dhai | ढाई | 2.5 (replaces "saadhe do") | dhai kilo; dhai sau = 250 |

**Kannada equivalents.**

| Word | Script | Meaning | Examples |
|---|---|---|---|
| kaalu | ಕಾಲು | 1/4 | kaal kilo = 250 g |
| ardha | ಅರ್ಧ | 1/2 | ardha kilo = 500 g |
| mukkaalu | ಮುಕ್ಕಾಲು | 3/4 | mukkaal kilo = 750 g |
| X-oo-kaalu | ಒಂದೂಕಾಲು, ಎರಡೂಕಾಲು | X + 1/4 | onduukaalu = 1.25; eraduukaalu = 2.25 |
| X-oo-vare | ಒಂದೂವರೆ, ಎರಡೂವರೆ, ಮೂರೂವರೆ | X + 1/2 (used for all X, including 1 and 2) | onduvare = 1.5; eraduvare = 2.5; ombattuvare = 9.5 |
| X-oo-mukkaalu | ಎರಡೂ ಮುಕ್ಕಾಲು | X + 3/4 (counts up, unlike Hindi paune, which counts down) | eradoo mukkaalu = 2.75 |
| ... kaal kadime | ಮೂರಕ್ಕೆ ಕಾಲು ಕಡಿಮೆ | (X − 1/4); rare | mooRakke kaal kadime = 2.75 |

Key difference: **Hindi "paune teen" (2.75) counts down from 3, while Kannada usually counts up from 2 ("eradoo mukkaalu")**. A parser must not assume the same direction for both languages.

**How weights and measurements are actually spoken.** Spoken patterns observed in practice:

| Value | Hindi (common spoken forms) | Kannada (common spoken forms) | Normalised |
|---|---|---|---|
| 2.8 kg (newborn) | "do point aath kilo"; "do kilo aath sau gram"; "teen kilo se thoda kam" | "eradu point entu kilo"; "eradu kilo entu nooru graam"; "eradu kejee entnooru" | 2.8 kg |
| 2.5 kg | "dhai kilo"; "do kilo paanch sau gram"; "do point paanch" | "eraduvare kilo"; "eradu kilo ainooru graam" | 2.5 kg |
| 52 kg 500 g (mother) | "baavan kilo paanch sau gram"; "saadhe baavan kilo"; "baavan point paanch" | "aivatteradu kilo ainooru graam"; "aivatteraduvare kilo"; "fifty two point five" (English) | 52.5 kg |
| Hb 9.5 g/dL | "saadhe nau"; "nau point paanch"; "HB nine point five" | "ombattuvare"; "ombattu point aidu" | 9.5 |
| Hb 10.2 | "das point do" | "hattu point eradu" | 10.2 |
| BP 120/80 | "ek sau bees by assi"; "one twenty by eighty"; "bees assi" (dropping the hundreds) | "noora ippattu by embattu"; "one twenty eighty" | 120/80 |
| Temp 101.4 °F | "ek sau ek point chaar"; "ek sau ek degree" | "noora ondu point naalku"; "noora ondu digri" | 101.4 °F |
| 3 months 10 days | "teen mahine das din" | "mooru tingalu hattu dina" | 3 mo 10 d |

Kannada hundreds, for the parser (UNSOURCED-linguistic): ನೂರು nooru (100), ಇನ್ನೂರು innooru (200), ಮುನ್ನೂರು munnooru (300), ನಾನೂರು naanooru (400), ಐನೂರು ainooru (500), ಆರುನೂರು aarunooru (600), ಏಳುನೂರು elunooru (700), ಎಂಟುನೂರು entunooru (800), ಒಂಬೈನೂರು ombainooru (900), ಸಾವಿರ saavira (1000).
- The combining form "noora" is used in compounds: noora ippattu = 120.
- Hindi: सौ sau, दो सौ do sau, हज़ार hazaar, लाख laakh, करोड़ karod.

### 4b. Relative dates and disambiguation

**Hindi.**

| Expression | Script | Meaning | Disambiguation |
|---|---|---|---|
| aaj | आज | today | none needed |
| kal | कल | yesterday OR tomorrow | Decided by verb tense (rules R7 and R8) |
| parson | परसों | day before yesterday OR day after tomorrow | Same rule as kal |
| narson | नरसों | ±3 days | Rare and regional (UNSOURCED); confirm it back to the user |
| abhi | अभी | now | none needed |
| is hafte / agle hafte / pichhle hafte | इस/अगले/पिछले हफ्ते | this / next / last week | "hafta" is also used for Saturday in some dialects; treat it as a week |
| agle mahine / pichhle mahine | अगले/पिछले महीने | next / last month | none needed |
| mahine ki 15 tareekh | महीने की पंद्रह तारीख | the 15th of [this] month | Month implicit: use the current month if day ≥ today for future verbs, otherwise the next month; confirm with the user |
| 15 tareekh ko | पंद्रह तारीख को | on the 15th | Same as above |
| somvaar ko | सोमवार को | on Monday | Next occurrence for future verbs, last for past; confirm |
| X din pehle / X din baad | X दिन पहले / बाद | X days ago / in X days | none needed |
| X mahine ka garbh | X महीने का गर्भ | X months pregnant | This is a **duration**, not a date; never convert it to an EDD |

**Kannada.**

| Expression | Script | Meaning |
|---|---|---|
| indu / ivattu / ivaga | ಇಂದು / ಇವತ್ತು / ಈಗ | today / today (colloquial) / now |
| naale | ನಾಳೆ | tomorrow (unambiguous) |
| ninne | ನಿನ್ನೆ | yesterday (unambiguous) |
| naadiddu | ನಾಡಿದ್ದು | day after tomorrow |
| monne | ಮೊನ್ನೆ | day before yesterday. Colloquially it also means "a few days ago", so flag it as vague |
| ee vaara / mundina vaara / kaleda vaara (hoda vaara) | ಈ ವಾರ / ಮುಂದಿನ ವಾರ / ಕಳೆದ (ಹೋದ) ವಾರ | this / next / last week |
| ee tingalu / mundina tingalu / kaleda tingalu | ಈ / ಮುಂದಿನ / ಕಳೆದ ತಿಂಗಳು | this / next / last month |
| tingala hadinaidane taareekhu | ತಿಂಗಳ ಹದಿನೈದನೇ ತಾರೀಖು | 15th of the month. Ordinal suffix -ane/-ne |
| hadinaidakke | ಹದಿನೈದಕ್ಕೆ | on the 15th (dative) |
| X dina mundhe / X dinada hinde | X ದಿನ ಮುಂದೆ / X ದಿನದ ಹಿಂದೆ | in X days / X days ago |
| somavaara | ಸೋಮವಾರ | Monday |

**Weekdays.**

| English | Hindi | Kannada |
|---|---|---|
| Mon | सोमवार somvaar | ಸೋಮವಾರ somavaara |
| Tue | मंगलवार mangalvaar | ಮಂಗಳವಾರ mangalavaara |
| Wed | बुधवार budhvaar | ಬುಧವಾರ budhavaara |
| Thu | गुरुवार guruvaar (also बृहस्पतिवार brihaspativaar) | ಗುರುವಾರ guruvaara |
| Fri | शुक्रवार shukravaar | ಶುಕ್ರವಾರ shukravaara |
| Sat | शनिवार shanivaar | ಶನಿವಾರ shanivaara |
| Sun | रविवार ravivaar (also इतवार itvaar) | ಭಾನುವಾರ bhaanuvaara (also ರವಿವಾರ ravivaara) |

**Months.** Both languages use the English month names in everyday ASHA speech.

| # | Hindi | Kannada |
|---|---|---|
| 1 | जनवरी janvari | ಜನವರಿ janavari |
| 2 | फरवरी farvari | ಫೆಬ್ರವರಿ febravari |
| 3 | मार्च maarch | ಮಾರ್ಚ್ maarch |
| 4 | अप्रैल aprail | ಏಪ್ರಿಲ್ epril |
| 5 | मई mai | ಮೇ me |
| 6 | जून joon | ಜೂನ್ joon |
| 7 | जुलाई julaai | ಜುಲೈ julai |
| 8 | अगस्त agast | ಆಗಸ್ಟ್ aagast |
| 9 | सितंबर sitambar | ಸೆಪ್ಟೆಂಬರ್ septembar |
| 10 | अक्टूबर aktoobar | ಅಕ್ಟೋಬರ್ aktobar |
| 11 | नवंबर navambar | ನವೆಂಬರ್ navembar |
| 12 | दिसंबर disambar | ಡಿಸೆಂಬರ್ disembar |

Note: ASR may output "मई" (mai, May) where the speaker meant "में" (mein, "in"), and vice versa. Accept "mai" as May only when it is adjacent to a day number or year.

### 4c. Verbalising for TTS

**Gnani's TTS guidance.**
- The Timbre docs say normalisation runs automatically [S10], but the inference page says "Pass numbers, dates, and currency as spoken words" [S11].
- Kannada normalisation is "under continuous refinement" [S10].
- With `language=auto`, "point" and "percent" stay in English [S10].
- For non-English IDs, "Every other language spells each digit individually" [S10].
- `23/06` without a year is read as a fraction, not a date [S10].

**Decision: always send words, and set `language` explicitly (`hi` or `kn`).**

**Numbers 0 to 100.**
- **Hindi.** Romanised forms were checked against Wikipedia "Hindustani numerals" [S15] (SECONDARY). The Devanagari spellings are UNSOURCED-linguistic, and accepted variants exist: छह/छः, उन्यासी/उनासी, इक्यावन/इकावन, बानवे/बयानवे, नब्बे/नव्वे.
- **Kannada.** 0 to 21, the tens, and 100 were checked against Wikibooks "Kannada/Numbers" [S16] (SECONDARY). The 21 to 99 compounds are **rule-generated (UNSOURCED-linguistic)**:
  - Vowel-initial units join with ತ್ತ plus the vowel sign: ಇಪ್ಪತ್ತೊಂದು.
  - ಮೂರು and ನಾಲ್ಕು join with ತ್: ಇಪ್ಪತ್ಮೂರು, ಇಪ್ಪತ್ನಾಲ್ಕು.
  - Colloquial speech also has ಇಪ್ಪತ್ತ್ಮೂರು or ippattmooru.
  - Romanisation is ASCII, with long vowels doubled.

| n | Hindi (Devanagari) | Hindi (roman) | Kannada (script) | Kannada (roman) | Note |
|---|---|---|---|---|---|
| 0 | शून्य | shoonya | ಸೊನ್ನೆ | sonne |  |
| 1 | एक | ek | ಒಂದು | ondu |  |
| 2 | दो | do | ಎರಡು | eradu |  |
| 3 | तीन | teen | ಮೂರು | mooru |  |
| 4 | चार | chaar | ನಾಲ್ಕು | naalku |  |
| 5 | पाँच | paanch | ಐದು | aidu |  |
| 6 | छह | chhah | ಆರು | aaru |  |
| 7 | सात | saat | ಏಳು | elu |  |
| 8 | आठ | aath | ಎಂಟು | entu |  |
| 9 | नौ | nau | ಒಂಬತ್ತು | ombattu |  |
| 10 | दस | das | ಹತ್ತು | hattu |  |
| 11 | ग्यारह | gyaarah | ಹನ್ನೊಂದು | hannondu |  |
| 12 | बारह | baarah | ಹನ್ನೆರಡು | hanneradu |  |
| 13 | तेरह | terah | ಹದಿಮೂರು | hadimooru |  |
| 14 | चौदह | chaudah | ಹದಿನಾಲ್ಕು | hadinaalku |  |
| 15 | पंद्रह | pandrah | ಹದಿನೈದು | hadinaidu |  |
| 16 | सोलह | solah | ಹದಿನಾರು | hadinaaru |  |
| 17 | सत्रह | satrah | ಹದಿನೇಳು | hadinelu |  |
| 18 | अठारह | athaarah | ಹದಿನೆಂಟು | hadinentu |  |
| 19 | उन्नीस | unnees | ಹತ್ತೊಂಬತ್ತು | hattombattu |  |
| 20 | बीस | bees | ಇಪ್ಪತ್ತು | ippattu |  |
| 21 | इक्कीस | ikkees | ಇಪ್ಪತ್ತೊಂದು | ippattondu | rule-generated |
| 22 | बाईस | baaees | ಇಪ್ಪತ್ತೆರಡು | ippatteradu | rule-generated |
| 23 | तेईस | teyees | ಇಪ್ಪತ್ಮೂರು | ippatmooru | rule-generated |
| 24 | चौबीस | chaubees | ಇಪ್ಪತ್ನಾಲ್ಕು | ippatnaalku | rule-generated |
| 25 | पच्चीस | pachchees | ಇಪ್ಪತ್ತೈದು | ippattaidu | rule-generated |
| 26 | छब्बीस | chhabbees | ಇಪ್ಪತ್ತಾರು | ippattaaru | rule-generated |
| 27 | सत्ताईस | sattaaees | ಇಪ್ಪತ್ತೇಳು | ippattelu | rule-generated |
| 28 | अट्ठाईस | atthaaees | ಇಪ್ಪತ್ತೆಂಟು | ippattentu | rule-generated |
| 29 | उनतीस | untees | ಇಪ್ಪತ್ತೊಂಬತ್ತು | ippattombattu | rule-generated |
| 30 | तीस | tees | ಮೂವತ್ತು | moovattu |  |
| 31 | इकतीस | iktees | ಮೂವತ್ತೊಂದು | moovattondu | rule-generated |
| 32 | बत्तीस | battees | ಮೂವತ್ತೆರಡು | moovatteradu | rule-generated |
| 33 | तैंतीस | taintees | ಮೂವತ್ಮೂರು | moovatmooru | rule-generated |
| 34 | चौंतीस | chauntees | ಮೂವತ್ನಾಲ್ಕು | moovatnaalku | rule-generated |
| 35 | पैंतीस | paintees | ಮೂವತ್ತೈದು | moovattaidu | rule-generated |
| 36 | छत्तीस | chhattees | ಮೂವತ್ತಾರು | moovattaaru | rule-generated |
| 37 | सैंतीस | saintees | ಮೂವತ್ತೇಳು | moovattelu | rule-generated |
| 38 | अड़तीस | adtees | ಮೂವತ್ತೆಂಟು | moovattentu | rule-generated |
| 39 | उनतालीस | untaalees | ಮೂವತ್ತೊಂಬತ್ತು | moovattombattu | rule-generated |
| 40 | चालीस | chaalees | ನಲವತ್ತು | nalavattu |  |
| 41 | इकतालीस | iktaalees | ನಲವತ್ತೊಂದು | nalavattondu | rule-generated |
| 42 | बयालीस | bayaalees | ನಲವತ್ತೆರಡು | nalavatteradu | rule-generated |
| 43 | तैंतालीस | taintaalees | ನಲವತ್ಮೂರು | nalavatmooru | rule-generated |
| 44 | चवालीस | chavaalees | ನಲವತ್ನಾಲ್ಕು | nalavatnaalku | rule-generated |
| 45 | पैंतालीस | paintaalees | ನಲವತ್ತೈದು | nalavattaidu | rule-generated |
| 46 | छियालीस | chhiyaalees | ನಲವತ್ತಾರು | nalavattaaru | rule-generated |
| 47 | सैंतालीस | saintaalees | ನಲವತ್ತೇಳು | nalavattelu | rule-generated |
| 48 | अड़तालीस | adtaalees | ನಲವತ್ತೆಂಟು | nalavattentu | rule-generated |
| 49 | उनचास | unchaas | ನಲವತ್ತೊಂಬತ್ತು | nalavattombattu | rule-generated |
| 50 | पचास | pachaas | ಐವತ್ತು | aivattu |  |
| 51 | इक्यावन | ikyaavan | ಐವತ್ತೊಂದು | aivattondu | rule-generated |
| 52 | बावन | baavan | ಐವತ್ತೆರಡು | aivatteradu | rule-generated |
| 53 | तिरेपन | tirepan | ಐವತ್ಮೂರು | aivatmooru | rule-generated |
| 54 | चौवन | chauvan | ಐವತ್ನಾಲ್ಕು | aivatnaalku | rule-generated |
| 55 | पचपन | pachpan | ಐವತ್ತೈದು | aivattaidu | rule-generated |
| 56 | छप्पन | chhappan | ಐವತ್ತಾರು | aivattaaru | rule-generated |
| 57 | सत्तावन | sattaavan | ಐವತ್ತೇಳು | aivattelu | rule-generated |
| 58 | अट्ठावन | atthaavan | ಐವತ್ತೆಂಟು | aivattentu | rule-generated |
| 59 | उनसठ | unsath | ಐವತ್ತೊಂಬತ್ತು | aivattombattu | rule-generated |
| 60 | साठ | saath | ಅರವತ್ತು | aravattu |  |
| 61 | इकसठ | iksath | ಅರವತ್ತೊಂದು | aravattondu | rule-generated |
| 62 | बासठ | baasath | ಅರವತ್ತೆರಡು | aravatteradu | rule-generated |
| 63 | तिरसठ | tirsath | ಅರವತ್ಮೂರು | aravatmooru | rule-generated |
| 64 | चौंसठ | chaunsath | ಅರವತ್ನಾಲ್ಕು | aravatnaalku | rule-generated |
| 65 | पैंसठ | painsath | ಅರವತ್ತೈದು | aravattaidu | rule-generated |
| 66 | छियासठ | chhiyaasath | ಅರವತ್ತಾರು | aravattaaru | rule-generated |
| 67 | सड़सठ | sadsath | ಅರವತ್ತೇಳು | aravattelu | rule-generated |
| 68 | अड़सठ | adsath | ಅರವತ್ತೆಂಟು | aravattentu | rule-generated |
| 69 | उनहत्तर | unhattar | ಅರವತ್ತೊಂಬತ್ತು | aravattombattu | rule-generated |
| 70 | सत्तर | sattar | ಎಪ್ಪತ್ತು | eppattu |  |
| 71 | इकहत्तर | ikhattar | ಎಪ್ಪತ್ತೊಂದು | eppattondu | rule-generated |
| 72 | बहत्तर | bahattar | ಎಪ್ಪತ್ತೆರಡು | eppatteradu | rule-generated |
| 73 | तिहत्तर | tihattar | ಎಪ್ಪತ್ಮೂರು | eppatmooru | rule-generated |
| 74 | चौहत्तर | chauhattar | ಎಪ್ಪತ್ನಾಲ್ಕು | eppatnaalku | rule-generated |
| 75 | पचहत्तर | pachhattar | ಎಪ್ಪತ್ತೈದು | eppattaidu | rule-generated |
| 76 | छिहत्तर | chhihattar | ಎಪ್ಪತ್ತಾರು | eppattaaru | rule-generated |
| 77 | सतहत्तर | sathattar | ಎಪ್ಪತ್ತೇಳು | eppattelu | rule-generated |
| 78 | अठहत्तर | athhattar | ಎಪ್ಪತ್ತೆಂಟು | eppattentu | rule-generated |
| 79 | उन्यासी | unyaasi | ಎಪ್ಪತ್ತೊಂಬತ್ತು | eppattombattu | rule-generated |
| 80 | अस्सी | assi | ಎಂಬತ್ತು | embattu |  |
| 81 | इक्यासी | ikyaasi | ಎಂಬತ್ತೊಂದು | embattondu | rule-generated |
| 82 | बयासी | bayaasi | ಎಂಬತ್ತೆರಡು | embatteradu | rule-generated |
| 83 | तिरासी | tiraasi | ಎಂಬತ್ಮೂರು | embatmooru | rule-generated |
| 84 | चौरासी | chauraasi | ಎಂಬತ್ನಾಲ್ಕು | embatnaalku | rule-generated |
| 85 | पचासी | pachaasi | ಎಂಬತ್ತೈದು | embattaidu | rule-generated |
| 86 | छियासी | chhiyaasi | ಎಂಬತ್ತಾರು | embattaaru | rule-generated |
| 87 | सत्तासी | sattaasi | ಎಂಬತ್ತೇಳು | embattelu | rule-generated |
| 88 | अट्ठासी | atthaasi | ಎಂಬತ್ತೆಂಟು | embattentu | rule-generated |
| 89 | नवासी | navaasi | ಎಂಬತ್ತೊಂಬತ್ತು | embattombattu | rule-generated |
| 90 | नब्बे | nabbe | ತೊಂಬತ್ತು | tombattu |  |
| 91 | इक्यानवे | ikyaanve | ತೊಂಬತ್ತೊಂದು | tombattondu | rule-generated |
| 92 | बानवे | baanve | ತೊಂಬತ್ತೆರಡು | tombatteradu | rule-generated |
| 93 | तिरानवे | tiraanve | ತೊಂಬತ್ಮೂರು | tombatmooru | rule-generated |
| 94 | चौरानवे | chauraanve | ತೊಂಬತ್ನಾಲ್ಕು | tombatnaalku | rule-generated |
| 95 | पचानवे | pachaanve | ತೊಂಬತ್ತೈದು | tombattaidu | rule-generated |
| 96 | छियानवे | chhiyaanve | ತೊಂಬತ್ತಾರು | tombattaaru | rule-generated |
| 97 | सत्तानवे | sattaanve | ತೊಂಬತ್ತೇಳು | tombattelu | rule-generated |
| 98 | अट्ठानवे | atthaanve | ತೊಂಬತ್ತೆಂಟು | tombattentu | rule-generated |
| 99 | निन्यानवे | ninyaanve | ತೊಂಬತ್ತೊಂಬತ್ತು | tombattombattu | rule-generated |
| 100 | सौ | sau | ನೂರು | nooru |  |

**Decimals.** Say "point", then each digit after it separately.
- Hindi: 9.5 → "नौ पॉइंट पाँच" (nau point paanch). Formal: "नौ दशमलव पाँच" (Gnani renders दशमलव only when `language=hi` is explicit [S10]). 2.85 → "दो पॉइंट आठ पाँच", not "do point pachaasi".
- Kannada: 9.5 → "ಒಂಬತ್ತು ಪಾಯಿಂಟ್ ಐದು" (ombattu paayint aidu). Gnani's own Kannada example uses ಪಾಯಿಂಟ್ [S10]. The formal word is ದಶಮಾಂಶ.
- For TTS, prefer "point" over the fraction words, because it is unambiguous. If you need to match how ASHAs speak, the fraction words (saadhe nau, ombattuvare) are fine for .5 only.

**IDs digit by digit.** Mobile numbers, RCH ID, ABHA, Aadhaar, OTP and similar:
- Read each digit separately, in groups. Mobile numbers go 3-3-4, which is Gnani's convention [S10]. Aadhaar goes 4-4-4 [S10]. For RCH and ABHA, use groups of 4. RCH ID length and ABHA's 14-digit format are UNVERIFIED in this pass.
- In Hindi, do not compress "double" (Gnani says only English compresses [S10]). Zero is "ज़ीरो" (zero) in speech, more common than शून्य.
- In Kannada, zero is "ಸೊನ್ನೆ" (sonne).
- Insert a comma between groups to force a pause.
- Example (Hindi): `98450 12345` → "नौ आठ चार, पाँच शून्य एक, दो तीन चार पाँच".

**Dates.**
- **Hindi:** day (cardinal), then month name, then year. 15/03/2026 → "पंद्रह मार्च दो हज़ार छब्बीस" (pandrah maarch do hazaar chhabbees). Day only: "पंद्रह तारीख" (pandrah taareekh). Ordinal day words (पंद्रहवीं) are rare in speech; avoid them.
- **Kannada:** two common orders:
  - Month then cardinal day: "ಮಾರ್ಚ್ ಹದಿನೈದು" (maarch hadinaidu).
  - Ordinal day then month: "ಹದಿನೈದನೇ ಮಾರ್ಚ್" (hadinaidane maarch).
  - Year: "ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಾರು" (eradu saavirada ippattaaru).
  - Recommended TTS form: "ಮಾರ್ಚ್ ಹದಿನೈದು, ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಾರು".
  - Ordinal suffix: cardinal minus the final ು, plus ನೇ (ondu → ಒಂದನೇ, eradu → ಎರಡನೇ, hadinaidu → ಹದಿನೈದನೇ). UNSOURCED-linguistic.
- **Weekday plus date** (helps comprehension): Hindi "सोमवार, सोलह मार्च"; Kannada "ಸೋಮವಾರ, ಮಾರ್ಚ್ ಹದಿನಾರು".
- **Gnani caveat:** never send `15/03` without a year [S10].

### Parsing rules for the number and date normaliser

1. **Request words explicitly from STT.** Set `format=codemix` and `language_code=kn-IN,hi-IN,en-IN` on Prisma v3.0. Numbers then arrive as native words and acronyms stay in Latin [S9]. Never rely on the default format, which differs by language code.
2. **Tokenise across three scripts.** Map Devanagari, Kannada and Latin number words to integers using the 0 to 100 tables, plus English words (one to ninety-nine) and digits. Accept the listed spelling variants and the colloquial final-vowel drop (ond, erad, aid, entu → ent).
3. **Compose by scale.** Use units < 100, then sau/nooru/noora (×100), hazaar/saavira/saavirada (×1000) and laakh/lakh (×100000). For Kannada hundreds (innooru, munnooru, ainooru and so on), use the lexical table, not composition.
4. **Apply fraction modifiers before scale:**
   - sava X = X + 0.25, saadhe X = X + 0.5, paune X = X − 0.25, dedh = 1.5, dhai = 2.5, paav = 0.25, paun = 0.75, aadha = 0.5.
   - Kannada: X-ookaalu = X + 0.25, X-oovare = X + 0.5, X-oo mukkaalu = X + 0.75, ardha = 0.5, kaal = 0.25, mukkaal = 0.75.
   - The modifier scales with the following unit: "dhai sau" = 250, "dedh hazaar" = 1500.
5. **Decimals.** "point" / पॉइंट / ಪಾಯಿಂಟ್ / दशमलव / ದಶಮಾಂಶ followed by number words: read each following token as a single digit if every token is 0 to 9. If one token is 10 to 99 (for example "do point pachaasi"), treat it as two decimal digits, and mark the value low-confidence so it is read back.
6. **Unit compounds.** `N kilo M gram` = N + M/1000 kg. `N kilo` followed directly by a bare number < 1000 inside a weight context = N + M/1000 ("do kilo aath sau" = 2.8). Reject results outside plausible ranges and ask again: newborn 0.5 to 6 kg, mother 25 to 150 kg, Hb 3 to 20, systolic BP 60 to 250, diastolic BP 30 to 150, temperature 93 to 108 °F. These ranges are validation guards only, never clinical interpretation.
7. **BP pairs.** "X by Y" / "X over Y" / "X बाई Y" / "X ಬೈ Y", or two numbers in a BP context, give systolic/diastolic. Expand the dropped hundreds ("bees assi" after "BP" means 120/80) **only** if the first number is < 100 and the second is less than the first. Always confirm it back to the user.
8. **Hindi kal/parson by tense:**
   - Past markers (था/थी/थे, गया/गई/गए, किया/की/किए, हुआ/हुई/हुए, -आ/-ई/-ए perfective, "लगवाया", "दिया") mean −1 (or −2 for parson).
   - Future markers (-ेगा/-ेगी/-ेंगे/-ूँगा, "है" with an infinitive as in "जाना है", "आना है", "लगेगा", "होगा") mean +1 (or +2).
   - Present habitual or no verb ("कल टीका") is ambiguous. **Ask** with a disambiguating read-back ("kal matlab [weekday]?").
9. **Kannada relative words map directly:** naale = +1, ninne = −1, naadiddu = +2, monne = −2 (flag "approximate"), indu/ivattu = 0. If Hindi "kal" appears inside Kannada speech, apply rule 8 using the Kannada tense: past -ತು/-ದೆ/-ಿದ್ದ means past; future -ುತ್ತೇನೆ/-ುತ್ತಾರೆ/-ಬೇಕು means future.
10. **Week and month offsets.** agle/mundina = +1, pichhle/kaleda/hoda = −1, is/ee = 0. Return a date **range** (week or month), not a single day, unless a weekday is also given.
11. **Day-only dates** ("15 tareekh", "hadinaidane taareekhu"). Resolve to the nearest such date in the direction given by tense (rule 8 or 9). Then always echo the full date back ("पंद्रह दिसंबर, ठीक है?").
12. **Full dates.** Accept day-month-year in either order, month names in Hindi, Kannada or English script, and numeric months spoken as numbers ("teen tareekh chaar mahina" = 3 April). Assume DD/MM, never MM/DD.
13. **Durations are not dates.** "X mahine ka garbh", "X tingalu", "X hafte ka bachcha" are durations. Store them as durations. **Never** convert them into LMP/EDD or vaccine due dates (product rule: no schedule calculation).
14. **IDs.** For sequences in an ID context (mobile, RCH, ABHA, Aadhaar, OTP), keep the digit string exactly. Do not compose "nau aath" into 98. Accept "double X" / "triple X". Validate length (mobile 10, Aadhaar 12; others UNVERIFIED) and read back in groups.
15. **TTS output.** Re-verbalise every number with the 4c rules and tables before calling Timbre. Set `language` explicitly. Separate ID groups with commas. Never send a bare `dd/mm`.

---

## Sources

- [S1] MoHFW / National Health Mission. *National Immunization Schedule (NIS) for Infants, Children and Pregnant Women* (age-wise and vaccine-wise tables). PDF, metadata 29 May 2020, pages 1 to 3. https://nhm.gov.in/New_Updates_2018/NHM_Components/Immunization/report/National_%20Immunization_Schedule.pdf (text extracted locally). The MoHFW copy at https://www.mohfw.gov.in/sites/default/files/National%20Immunization%20Schedule.pdf returned 403.
- [S2] PIB Research Unit, Government of India. *Celebrating the Power of Vaccines*, 17 March 2026. Sections "Universal Immunisation Programme", "National Immunisation Schedule", "Recent Vaccine Launches & Programmes" (HPV campaign 28 February 2026; indigenous Td 21 February 2026). https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/mar/doc2026320830601.pdf
- [S3] National Health Mission Himachal Pradesh. *Immunization* (NIS table). https://nhm.hp.gov.in/immmunization (official state page; Vitamin A wording differs from S1).
- [S4] fIPV third dose rollout from 1 January 2023 (SECONDARY: news reports of state circulars). DT Next, "DPH issues guidelines on administration of fractional dose of polio vax", https://www.dtnext.in/amp/story/news/tamilnadu/dph-issues-guidelines-on-administration-of-fractional-dose-of-polio-vax ; The Tribune, "Campaign for third dose of polio vaccine begins", January 2023, https://www.tribuneindia.com/news/jalandhar/campaign-for-third-dose-of-polio-vaccine-begins-467551 . Seen via search snippets only; pages not fully read.
- [S5] MoHFW. *Universal Immunization Programme* (JE in 206 or 215 endemic districts; JE-1 9 to 12 months, JE-2 16 to 24 months). https://mohfw.gov.in/sites/default/files/41016395871489662752.pdf (seen via search snippet only).
- [S6] MoHFW. HBNC/HBYC portal, "About" (HBNC visits on day 3, 7, 14, 21, 28, 42, plus day 1 for home births; HBYC at 3, 6, 9, 12, 15 months). https://hbnc-hbyc.mohfw.gov.in/about (seen via search snippet; the site refused a direct connection).
- [S7] NHM Himachal Pradesh. *HBNC*. https://nhm.hp.gov.in/child-health/community-based-care/hbnc (search snippet).
- [S8] Anemia Mukt Bharat IFA colour coding (red for pregnant and lactating women and WRA, blue for 10 to 19 years, pink for 5 to 9 years, syrup for 6 to 59 months). NHM HP, https://nhm.hp.gov.in/child-health/facility-based ; Vikaspedia (SECONDARY), https://en.vikaspedia.in/viewcontent/health/health-campaigns/anemia-mukt-bharat . The age bands differ slightly between the two.
- [S9] Gnani.ai. *Prisma v3.0* model docs: parameters `keyterms` (up to 200), `format` (verbatim/transcribe/codemix/transliterate), default format by language code, `kn-IN`/`hi-IN` codes. https://docs.gnani.ai/api/STT/models/prisma-v3.md (accessed 13 November 2026). Release coverage (SECONDARY): Let's Data Science, "Gnani AI launches Prisma v3.0", 28 October 2026, https://letsdatascience.com/news/gnani-ai-launches-prisma-v30-speech-to-text-model-for-indian-7163adda
- [S10] Gnani.ai. *TTS input formatting / text normalisation guide*. https://docs.gnani.ai/api/TTS/tts-input-formating.md (accessed 13 November 2026).
- [S11] Gnani.ai. *TTS inference* (`timbre-v3.0`; "Pass numbers, dates, and currency as spoken words"). https://docs.gnani.ai/api/TTS/tts-inference.md (accessed 13 November 2026).
- [S12] The South First. "'Thayi Card' to now record mental health status of pregnant women in Karnataka", 28 February 2023 (SECONDARY). https://thesouthfirst.com/news/thayi-card-to-now-record-pregnant-womens-mental-health-status
- [S13] Udayavani. "DK: Thayi Card given to 74,924 people in three years" (Thayi card is needed for JSY, Madilu and Prasooti Araike), about 2019 (SECONDARY). https://english.udayavani.com/article/dk-thayi-card-given-to-74924-people-in-three-years/716346
- [S14] myScheme (Government of India). *Thayi Bhagya*. https://www.myscheme.gov.in/schemes/thayi-bhagya (search snippet only).
- [S15] Wikipedia. "Hindustani numerals" (romanised 0 to 100) (SECONDARY). https://en.wikipedia.org/wiki/Hindustani_numerals
- [S16] Wikibooks. "Kannada/Numbers" (0 to 21, tens, 100) (SECONDARY). https://en.wikibooks.org/wiki/Kannada/Numbers

---

## Risks and open questions

1. **No frequency data.** The 199 terms are curated from programme documents, not counted from ASHA speech. The ranking is UNVERIFIED. Validate it with 2 to 3 Karnataka ASHAs, or with transcripts of real home-visit audio, before freezing the keyterm list.
2. **The 200-keyterm budget.** The CSV plus native-script variants is well over 200 strings.
   - Proposal: 100 Latin canonical or acronym forms (ANC, Td, IFA and so on, which stay Latin under `codemix`), 60 Kannada-script local words, and 40 Devanagari local words.
   - Do not spend keyterms on number words.
   - Test whether acronyms boost better as "ANC" or as "ಎ ಎನ್ ಸಿ". This is UNVERIFIED and needs an A/B test.
3. **All Hindi and Kannada spoken forms and misrecognition variants are UNSOURCED-linguistic.** In particular:
   - Kannada medical terms (ಬಾಣಂತಿ, ಗಿಣ್ಣು ಹಾಲು, ಹೊಕ್ಕುಳು, ಸೂಲಗಿತ್ತಿ) are standard Kannada but not checked against Karnataka ASHA training material.
   - North Karnataka (Dharwad/Kalaburagi) and coastal dialects will differ from Bengaluru/Mysuru Kannada.
   - Dakhni-Urdu speakers in North Karnataka will use Hindi/Urdu forms.
4. **Karnataka ASHA material in Kannada was not found.** The Karnataka ASHA module, the Thayi card scan, and the Kannada MCP card were not located in this pass. These are the best sources for the exact Kannada terms ASHAs are trained on. Next step: search karhfw.gov.in and nhm.karnataka.gov.in.
5. **UIP conflicts.** fIPV-3 and the national status of PCV are unresolved. JE-endemic status of Karnataka districts is unknown. HPV is a campaign, not yet a routine schedule entry. The assistant should **read the card, not compute**.
6. **Gnani TTS behaviour for Kannada numbers is unknown.** Their docs disagree, and Kannada TN is "under refinement". Test Timbre v3.0 with the 0 to 100 table and with the 21 to 99 rule-generated compounds (ಇಪ್ಪತ್ಮೂರು vs ಇಪ್ಪತ್ತಮೂರು) to see which sounds natural.
7. **The Prisma `format` default trap.** A single `hi-IN` returns digits, while `kn-IN` or `indic-auto` returns words [S9]. The normaliser must handle both (see rules 1 and 2), or `format` must always be set.
8. **Hindi kal/parson cannot always be resolved.** Short utterances ("kal tika") have no verb. The UX must confirm by reading back a weekday and date.
9. **Safety.** Numeric range guards (rule 6) are for catching ASR errors only. The assistant must not say "Hb is low", must not interpret BP, and must not tell the ASHA when the next vaccine is due. It can only read back what was captured and point to the MCP or Thayi card and the ANM.
