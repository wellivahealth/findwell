#!/usr/bin/env python3
"""
FindWell Directory — static site generator.

Run:  python3 build.py

Everything is generated from the DISCIPLINES and PROVIDERS lists below.
Edit those, re-run, commit. Every page ships as real HTML at a real URL,
so search engines can index each discipline, city, and practitioner.

Nothing from the "Internal, not published" section of the application form
appears anywhere in this file or in the generated output.
"""
import os, re, json, shutil, html, datetime, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, "public")   # Cloudflare serves this folder
YEAR = 2026
# Applications post to our own Worker at /api/apply, which stores them,
# emails you an approve link, and acknowledges the applicant.
# Set FORM_ENDPOINT to "" to fall back to opening a pre-filled email instead.
FORM_ENDPOINT = "/api/apply"

CONTACT_EMAIL = "info@findwelldirectory.com"   # where every enquiry lands

SITE = "https://findwelldirectory.com"   # <- set to the domain you attach; feeds canonical, og:url, sitemap

def _v(rel):
    """Content hash for an asset, so a changed file gets a new URL.
    Assets are cached for a year; without this, browsers keep serving the
    old CSS after a deploy and nothing appears to change."""
    try:
        with open(os.path.join(ROOT, "public", rel), "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:10]
    except FileNotFoundError:
        return "dev"

CSS_V  = _v("assets/site.css")
JS_V   = _v("assets/app.js")
IMG_V  = _v("assets/img/hero-1400.webp")
ABOUT_V = _v("assets/img/about-1400.webp")
BANNER_V = _v("assets/img/banner-1400.webp")
ABOUTB_V = _v("assets/img/aboutbanner-1400.webp")

SS = "https://images.squarespace-cdn.com/content/v1/6877e1d8fb99bd2e2af8e1ed/"
IMG = {
    "logo":  SS + "c4a2dd29-37ea-438e-aa6c-12715a6a508a/findwell-logo-trans.png",
    "about": SS + "194a0c8a-39fa-48a9-b260-2af2acae618b/Leonardo_Phoenix_10_Create_an_image_of_a_diverse_group_of_heal_1+%281%29.jpg",
}

DISCIPLINES = [
    dict(key="Ayurveda", label="Ayurveda", slug="ayurveda",
         note="Ayurvedic clinicians and educators. NAMA credentialed; no state licensure exists.",
         img="/assets/img/disciplines/ayurveda"),
    dict(key="Acupuncture", label="Acupuncture", slug="acupuncture",
         note="Licensed professionals — L.Ac.",
         img=SS + "1755277990849-EKKNDADU9C6IGG4FCL8D/unsplash-image-QgcdtM9rA5s.jpg"),
    dict(key="TCM", label="TCM", slug="traditional-chinese-medicine",
         note="Traditional Chinese Medicine — Dipl. O.M.",
         img=SS + "1755278047472-9EZGRJW7AO109Q8GK2D5/unsplash-image-ur2zmbseUIA.jpg"),
    dict(key="Naturopathy", label="Licensed naturopaths", slug="naturopathic-medicine",
         note="ND or NMD — licensed in Arizona.",
         img=SS + "1755278249101-I8FZPKRHUBB5G4P677O0/unsplash-image-KERVbxLVLiY.jpg"),
    dict(key="IntegrativeMedicine", label="Integrative & functional medicine (MD, DO, NP, PA, RN)",
         slug="integrative-functional-medicine",
         note="Physicians and licensed clinicians — MD, DO, NP, PA or RN — practising integrative or functional medicine. Board certification such as ABOIM, ABIHM, IFMCP or ABLM is published where held, and integrative training appears on every record, including when none is reported.",
         img="/assets/img/disciplines/integrative"),
    dict(key="Counseling", label="Counselors", slug="counseling",
         note="Licensed mental health professionals — LPC, LCSW, LMFT.",
         img=SS + "1757903674176-QK99BMSR1DQHPNWYLO3E/unsplash-image-F9DFuJoS9EU.jpg"),
    dict(key="Coaching", label="Health & wellness coaches", slug="health-wellness-coaching",
         note="Board certified coaches (NBC-HWC) and other non-clinical forms of support. No state licensure exists.",
         img="/assets/img/disciplines/coaching"),
    dict(key="Massage", label="Massage therapy", slug="massage-therapy",
         note="Licensed massage therapists — LMT, state licensed in Arizona.",
         img="/assets/img/disciplines/massage"),
    dict(key="Bodywork", label="Body work", slug="body-work",
         note="CranioSacral, structural integration, tuina and other manual therapies. Licensure varies by modality.",
         img=SS + "1755278329164-ATSTUR14YXFQDGE3ZFGI/unsplash-image-AV0KNliGvQc.jpg"),
    dict(key="EnergyMedicine", label="Energy healers", slug="energy-work",
         note="Reiki, Eden Energy Medicine, biofield therapies. Training shown; no licensure exists.",
         img=SS + "1755278519443-A0U3QGXU0WZX58E0VMA6/unsplash-image-QD7K3E9UTwI.jpg"),
    dict(key="Chiropractic", label="Chiropractors", slug="chiropractic",
         note="Doctor of Chiropractic — D.C., state licensed.",
         img=SS + "1755990861680-X13BU084AZ5IQFMMC1DT/unsplash-image-8qwYA4INVCk.jpg"),
    dict(key="Nutrition", label="Nutritionists", slug="nutrition",
         note="Registered dietitians (RD, RDN) and nutritionists, including CNS and BCHN. Licensure varies by state.",
         img="/assets/img/disciplines/nutrition"),
    dict(key="Herbalism", label="Herbology", slug="herbology",
         note="Registered herbalists and educators.",
         img=SS + "0362a0ef-8a7e-4341-80ff-30549e3acff8/shutterstock_2299524247.jpg"),
    dict(key="Farms", label="Local farmers", slug="local-farmers",
         note="Growers and CSAs.",
         img=SS + "1757901505698-RG39FAHW9EKTGN0RON06/unsplash-image-GYF0GAsUkYI.jpg"),
    dict(key="Grocers", label="Local grocers", slug="local-grocers",
         note="Locally owned and co-oped retail stores.",
         img=SS + "1757901575208-HKDJVCSSRJIJ8BLA3OAV/unsplash-image-WOxddhzhC1w.jpg"),
]

# ---------------------------------------------------------------------------
# Listings. Coordinates are approximate — geocode them properly before relying
# on distance search. `since` is derived from the years-in-practice answer.
# ---------------------------------------------------------------------------
PROVIDERS = [
    dict(slug="celia-hildebrand-acupuncture", name="Celia Hildebrand Acupuncture",
         person="Celia Hildebrand, L.Ac.", logo=None,
         categories=["Acupuncture", "EnergyMedicine", "Herbalism"],
         city="Tucson", state="AZ", zip="85704",
         address="7225 N. Paseo Del Norte, Tucson, AZ 85704",
         lat=32.3405, lng=-110.9880, telehealth=True,
         phone="(520) 283-2734", email="celia@acufromtheheart.com",
         website="http://www.acufromtheheart.com", social=[],
         credentials="Clinical doctorate in East Asian medicine; advanced Reiki and bioenergy practitioner",
         licensure="Arizona licensed acupuncturist — AZ LAC 001177",
         training="Six years and 3,500+ hours of training resulting in a clinical doctorate specialising in trauma care, physical rehabilitation and emotional resilience. Adjunctive methods include 25+ years with bioenergy and advanced Reiki.",
         since=2003, affiliations="—",
         pricing="Initial intake and treatment, 1.5 hr $150 · Follow-up, 1 hr $125 · Auricular acupuncture, 30 min $35 · Targeted hands or feet session $50 · Reduced rates for family members and for compressed protocols requiring frequent visits",
         payments="Cash, checks, credit, debit, PayPal, Zelle",
         insurance="Not accepted",
         blurb="Intuitive full-body East Asian medicine including acupuncture, tuina, gua sha, cupping, moxibustion and herbs.",
         long="Clinical sessions are based on science and practised with art and compassion, taking each person and their needs as the starting point."),

    dict(slug="hibiscus-acupuncture", name="Hibiscus Acupuncture",
         person="Frank Harris, L.Ac.", logo=None,
         categories=["Acupuncture", "TCM", "Bodywork"],
         city="Tucson", state="AZ", zip="85719",
         address="2450 East Speedway Boulevard #6, Tucson, AZ 85719",
         lat=32.2360, lng=-110.9430, telehealth=False,
         phone="(520) 609-8488", email="info@hibiscusacupuncture.com",
         website="http://www.hibiscusacupuncture.com",
         social=["https://www.instagram.com/hibiscusacupuncture"],
         credentials="Masters in Acupuncture and Oriental Medicine",
         licensure="Arizona licensed acupuncturist — AZ LAC-010717",
         training="Masters in Acupuncture and Oriental Medicine",
         since=2021, affiliations="—",
         pricing="New patient intake $120 · Return visit $85",
         payments="Insurance, cash, checks, credit, debit, HSA/FSA, PayPal, Venmo, Zelle",
         insurance="Accepted — verify your plan with the practice",
         blurb="Relieving pain, illness and emotional imbalance by bringing body, mind and spirit into harmony with traditional East Asian medicine, using acupuncture, tuina bodywork and herbal medicine.",
         long="My primary method of diagnosis and treatment is applied channel theory, though I am conversant in several schools of thought."),

    dict(slug="catalina-acupuncture", name="Catalina Acupuncture",
         person="Nathan Anderson, L.Ac.", logo=None,
         categories=["Acupuncture", "TCM", "Bodywork", "Herbalism"],
         city="Tucson", state="AZ", zip="85716",
         address="3208 E Fort Lowell Rd, Suite 106, Tucson, AZ 85716",
         lat=32.2705, lng=-110.9310, telehealth=True,
         phone="(520) 999-0080", email="CatalinaAcupuncturePLLC@gmail.com",
         website="http://www.CatalinaAcupuncture.com",
         social=["https://www.facebook.com/CatalinaAcupuncture",
                 "https://www.instagram.com/catalinaacupuncture/",
                 "https://www.linkedin.com/in/catalinaacupuncture/"],
         credentials="Master of Traditional Oriental Medicine",
         licensure="Arizona Acupuncture Board of Examiners #888 · originally licensed in California, California Acupuncture Board #9744",
         training="Emperor's College — Master of Traditional Oriental Medicine",
         since=2004, affiliations="—",
         pricing="First visit, 90 min $150 · Return visits, 60 min $100 · Herbal medicine varies",
         payments="Insurance, cash, checks, credit, debit, HSA/FSA, PayPal, Venmo",
         insurance="Accepted — verify your plan with the practice",
         blurb="Catalina Acupuncture provides solutions for pain and illness, blending traditional Chinese medicine with modern, results-driven techniques for chronic pain, injuries, stress and a range of health conditions.",
         long="Nathan Anderson, L.Ac., founder of Catalina Acupuncture, takes time to listen and creates personalised treatment plans that go beyond relieving symptoms to target the root cause. Care is delivered through acupuncture, cupping, herbal therapy and lifestyle guidance, with the goal of restoring balance in body, mind and spirit."),

    dict(slug="origins-health", name="Origins Health",
         person="Gwendolynn Diaz, MAS (AyD)", logo=None,
         categories=["Ayurveda"],
         city="Paonia", state="CO", zip="81428",
         address="130B Grand Ave, Suite 4, Paonia, CO 81428",
         lat=38.8686, lng=-107.5931, telehealth=True,
         phone="(970) 718-2740", email="gwen@origins-health.com",
         website="http://www.origins-health.com",
         social=["https://www.facebook.com/originshealth/",
                 "https://www.linkedin.com/in/gwendolynn-diaz-mas-ayd-437858"],
         credentials="MAS (AyD) Ayurveda, California College of Ayurveda; Integrative Ayurvedic Medicine; Certified Mental Health Integrative Medicine Practitioner",
         licensure="No state licensure exists for Ayurveda",
         training="Colorado State University, College of Applied Human Science; California College of Ayurveda — Doctor of Ayurveda, Medical Ayurvedic Specialist",
         since=2016, affiliations="—",
         pricing="Initial consultation $250 · Follow-up $150 · Membership-based care $69/month",
         payments="Cash, checks, credit, debit, HSA/FSA, PayPal, Venmo, Zelle",
         insurance="Not accepted",
         blurb="An integrative Ayurvedic practice offering personalised, root-cause care through telehealth and in-person visits, combining modern diagnostics with Ayurvedic medicine, herbal therapeutics, and diet and lifestyle support.",
         long="Sessions blend modern diagnostics with Ayurvedic principles and herbal therapeutics, addressing metabolic health, hormonal balance, biome adaptation and stress resilience. Care is ongoing and relationship-based, delivered through telehealth and in-person visits, with patients as active partners rather than passive recipients."),

    dict(slug="amitaayurveda", name="AmitaAyurveda",
         person="Amita Nathwani, MA", logo=SS + "1755282033154-A91OF7ETP49IX8QO83FV/amitaayurveda-logo-square-stack-notag-300dpi.png",
         categories=["Ayurveda", "Herbalism"],
         city="Tucson", state="AZ", zip="85712",
         address="2980 N Swan Rd, Tucson, AZ 85712",
         lat=32.2620, lng=-110.9060, telehealth=True,
         phone="(970) 946-2044", email="info@suryawellbeing.com",
         website="http://amitaayurveda.com",
         social=["https://www.instagram.com/amitaayurveda/"],
         credentials="MA in Ayurveda; NAMA; Ayurveda Professionals of Arizona",
         licensure="No state licensure exists for Ayurveda",
         training="MA in Ayurveda",
         since=2001, affiliations="NAMA; Ayurveda Professionals of Arizona",
         pricing="New patient $350 · Follow-up $135",
         payments="Cash, checks, credit, debit, HSA/FSA, PayPal, Venmo, Zelle",
         insurance="Not accepted",
         blurb="Ayurvedic assessment, dietary and lifestyle protocols, and herbal support. Virtual visits available.",
         long=""),

    dict(slug="ananda-ayurveda-yogalish", name="Ananda Ayurveda & Yogalish",
         person="Tanja Bungardt-Price", logo=SS + "1758690526106-4QQ77VKMG8LITYP4QJ26/Ananda%252BLogo.jpg",
         categories=["Ayurveda", "Herbalism"],
         city="Tucson", state="AZ", zip="85716",
         address="3501 E Kleindale Rd, Tucson, AZ 85716",
         lat=32.2540, lng=-110.9200, telehealth=True,
         phone="(520) 289-0238", email="YogalishAnanda@gmail.com",
         website="http://www.yogalish.com",
         social=["https://www.facebook.com/AnandaAyurvedaWellness",
                 "https://www.instagram.com/ananda_ayurveda_yogalish/"],
         credentials="NAMA Board Certified Ayurvedic Practitioner; Certified E-RYT 500 Yoga Teacher; Certified Qigong Teacher",
         licensure="No state licensure exists for Ayurveda",
         training="Ayurvedic Health Counselor and Ayurvedic Practitioner, both at Kanyakumari (WI); Yoga Teacher Training at Moksha Yoga (IL)",
         since=2013, affiliations="NAMA; CEU provider for NCBTMB and Yoga Alliance",
         pricing="Ayurvedic consultation, two-meeting package $240 · Follow-up visits $120 · Panchakarma quoted as consultation plus per treatment",
         payments="Cash, credit, debit, Venmo, Zelle",
         insurance="Not accepted",
         blurb="Ayurvedic consultations and education, including CEU provision for NCBTMB and Yoga Alliance.",
         long="A husband-and-wife practice. Consultations with Tanja run in two parts: a new-client intake of about two hours, then a report of findings of about an hour. Recommendations cover food as medicine, herbs, aromatherapy, lifestyle, yoga, meditation, sound and colour therapy, Ayurvedic treatments and cleanses. Bill, the panchakarma therapist, provides Ayurvedic treatments and holistic massage. The practice also runs workshops, trainings, lectures and classes, with CEUs for massage therapists, bodyworkers and yoga teachers."),

    dict(slug="thrive-chiropractic", name="Thrive: a chiropractic wellness center",
         person="Deva Nieuwenhuis, D.C.", logo=None,
         categories=["Chiropractic", "Bodywork"],
         city="Tucson", state="AZ", zip="85719",
         address="2571 N. 1st Ave, Tucson, AZ 85719",
         lat=32.2500, lng=-110.9720, telehealth=False,
         phone="(520) 622-8914", email="drdeva.usrey@gmail.com",
         website="http://www.thrivetucson.com", social=[],
         credentials="Doctor of Chiropractic",
         licensure="Arizona licensed chiropractor — license no. 7971",
         training="Undergraduate, University of Arizona; graduate, Life West Chiropractic College",
         since=2008, affiliations="—",
         pricing="First visit $100 · Adult adjustment $40 · Children's adjustment $25",
         payments="Cash, checks, credit, debit, HSA/FSA, Zelle",
         insurance="Not accepted",
         blurb="A chiropractic office that treats the whole person and looks for the root cause of your complaints.",
         long="We are dedicated to seeing a whole person, not just their pain, and working with them to live with as few limitations as possible. Appointment-only, so you never feel rushed and each concern is addressed."),

    dict(slug="emma-vasseur-wellbeing", name="Emma Vasseur: Wellbeing Coach",
         person="Emma Vasseur, NBC-HWC", logo=None,
         categories=["Bodywork", "EnergyMedicine", "Coaching"],
         city="Tucson", state="AZ", zip="85712",
         address="3071 N Swan Rd, Tucson, AZ 85712",
         lat=32.2660, lng=-110.9060, telehealth=True,
         phone="(612) 695-4063", email="hello@emmavasseur.com",
         website="http://emmavasseur.com", social=[],
         credentials="National Board Certified Health & Wellness Coach (NBC-HWC)",
         licensure="Not a licensed counsellor; coaching and bodywork are unlicensed in AZ",
         training="MA, Integrative Health & Wellbeing Coaching; Biodynamic Craniosacral education and training",
         since=2014, affiliations="—",
         pricing="Coaching, 3-month package $375/month ($1,125 total), six 50-minute sessions with email support · Biodynamic craniosacral, 60 min $95 · Evolutionary astrology reading, 60 min $125 or 90 min $150 · Coaching and astrology package $475/month for 3 months",
         payments="Cash, checks, credit, debit, PayPal",
         insurance="Not accepted",
         blurb="Support for people who want to feel healthier and more energised by making sustainable changes to daily life, bridging the gap between knowing what supports wellbeing and consistently practising it.",
         long="As a National Board Certified Health & Wellness Coach with a master's in Integrative Health & Wellbeing Coaching, I partner with clients on stress management, sleep, nutrition, movement, self-care and life balance through a personalised, strengths-based approach. I also offer biodynamic craniosacral therapy and evolutionary astrology as complementary services supporting nervous system regulation and self-awareness."),

    dict(slug="anita-kellman-end-of-life-doula", name="End of Life Doula",
         person="Anita Kellman", logo=None,
         categories=["Coaching"],
         city="Tucson", state="AZ", zip="85749",
         address="",   # applicant has no public premises; visits by arrangement
         lat=32.2830, lng=-110.7420, telehealth=True,
         phone="(520) 419-8632", email="doula@anitakellman.com",
         website="http://anitakellman.com", social=[],
         credentials="Certification from CareDoula",
         licensure="No state licensure exists for doula practice; not a licensed counsellor",
         training="Over 30 years in healthcare, witnessing, guiding and supporting patients through terminal illness",
         since=2021, affiliations="—",
         pricing="Hourly or package pricing, quoted to the client's needs",
         payments="Cash, Zelle",
         insurance="Not accepted",
         blurb="Creating and planning end-of-life care for patients and families, from practical work such as advance care planning through to legacy projects and emotional and spiritual support.",
         long="Non-medical support with gentle, intuitive guidance. I meet people where they are and offer presence — talking through fears, exploring what gives peace, creating rituals that feel meaningful, and holding space for grief as it unfolds. No public premises; visits are by arrangement, in person or remotely."),

    dict(slug="healing-options", name="Healing Options",
         person="Amy Schill, EEM-AP", logo=None,
         categories=["EnergyMedicine", "Coaching"],
         city="Tucson", state="AZ", zip="85704",
         address="855 W Calle Dadivoso, Tucson, AZ 85704",
         lat=32.3390, lng=-110.9950, telehealth=True,
         phone="(520) 548-9713", email="amy@healingoptions.com",
         website="http://healingoptions.com", social=[],
         credentials="Reiki Master Teacher; Eden Energy Medicine Advanced Practitioner (EEM-AP); Certified Nutrition Coach; Bach Flower Remedy Practitioner",
         licensure="No state licensure exists for energy medicine",
         training="Eden Method four-year certification programme graduate; Reiki Master Teacher attunement",
         since=2006, affiliations="—",
         pricing="$150 per hour",
         payments="Cash, checks, credit, debit, HSA/FSA, PayPal, Venmo, Zelle",
         insurance="Not accepted",
         blurb="I believe in the body's natural ability to heal and regain balance, and find it essential to focus on the whole being: body, mind and spirit.",
         long=""),
]

# ---------------------------------------------------------------------------
# Listings approved through the site (data/listings.json) are merged in here.
# The Worker writes that file when you click Approve in a notification email;
# entries below in PROVIDERS take precedence if a slug appears in both.
STATE_NAMES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
    "CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"District of Columbia",
    "FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois",
    "IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
    "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota",
    "MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
    "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
    "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon",
    "PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
    "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia",
    "WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
}

# Which board issues a licence, by discipline and state. Mirrors BOARDS in
# worker/index.js — used to turn a bare licence number into a statement that
# names the issuing authority.
LICENSE_BOARDS = {
    "Acupuncture":  {"AZ": "Arizona Acupuncture Board of Examiners",
                     "CA": "California Acupuncture Board"},
    "TCM":          {"AZ": "Arizona Acupuncture Board of Examiners"},
    "Naturopathy":  {"AZ": "Arizona Naturopathic Physicians Medical Board"},
    "Chiropractic": {"AZ": "Arizona Board of Chiropractic Examiners",
                     "CO": "Colorado State Board of Chiropractic Examiners",
                     "FL": "Florida Board of Chiropractic Medicine"},
    "Nutrition":    {"FL": "Florida Dietetics and Nutrition Practice Council"},
    "Massage":      {"AZ": "Arizona Massage Therapy Board"},
    "Bodywork":     {"AZ": "Arizona Massage Therapy Board"},
    "Counseling":   {"AZ": "Arizona Board of Behavioral Health Examiners",
                     "SC": "South Carolina Board of Examiners for Licensure of Professional Counselors, Marriage and Family Therapists, Addiction Counselors and Psycho-Educational Specialists"},
    "IntegrativeMedicine": {"AZ": "Arizona Medical Board"},
}


# First three digits of a ZIP identify the state. Used to catch "Arizona"
# truncated to "AR" by an earlier version of the intake code.
ZIP_STATE = [
    (995,999,'AK'),(850,865,'AZ'),(716,729,'AR'),(900,961,'CA'),(800,816,'CO'),
    (60,69,'CT'),(197,199,'DE'),(200,205,'DC'),(320,349,'FL'),(300,319,'GA'),
    (967,968,'HI'),(832,838,'ID'),(600,629,'IL'),(460,479,'IN'),(500,528,'IA'),
    (660,679,'KS'),(400,427,'KY'),(700,714,'LA'),(39,49,'ME'),(206,219,'MD'),
    (10,27,'MA'),(480,499,'MI'),(550,567,'MN'),(386,397,'MS'),(630,658,'MO'),
    (590,599,'MT'),(680,693,'NE'),(889,898,'NV'),(30,38,'NH'),(70,89,'NJ'),
    (870,884,'NM'),(100,149,'NY'),(270,289,'NC'),(580,588,'ND'),(430,459,'OH'),
    (730,749,'OK'),(970,979,'OR'),(150,196,'PA'),(28,29,'RI'),(290,299,'SC'),
    (570,577,'SD'),(370,385,'TN'),(750,799,'TX'),(840,847,'UT'),(50,59,'VT'),
    (220,246,'VA'),(980,994,'WA'),(247,268,'WV'),(530,549,'WI'),(820,831,'WY'),
]

PROVINCES = {
    "AB":"Alberta","BC":"British Columbia","MB":"Manitoba","NB":"New Brunswick",
    "NL":"Newfoundland and Labrador","NS":"Nova Scotia","NT":"Northwest Territories",
    "NU":"Nunavut","ON":"Ontario","PE":"Prince Edward Island","QC":"Quebec",
    "SK":"Saskatchewan","YT":"Yukon",
}
STATE_NAMES.update(PROVINCES)
NAME_TO_ABBR = {v.lower(): k for k, v in STATE_NAMES.items()}
NAME_TO_ABBR["québec"] = "QC"


def state_from_zip(zip_code):
    digits = re.sub(r"\D", "", str(zip_code or ""))
    if len(digits) not in (5, 9):        # not a US ZIP (Pune's 411007 read as Kentucky)
        return ""
    n = int(digits[:3])
    for lo, hi, ab in ZIP_STATE:
        if lo <= n <= hi:
            return ab
    return ""


def normalise(r):
    """Tidy what applicants type. People leave the scheme off a web address and
    give a licence number with no issuing body — both are published verbatim
    otherwise, and both look careless on the listing."""
    # a state that contradicts the ZIP is almost always a truncated name:
    # "Arizona" cut to two characters becomes "AR", which is Arkansas
    st = (r.get("state") or "").strip()
    by_name = NAME_TO_ABBR.get(st.lower())
    country = (r.get("country") or "").strip()
    abroad = country and country.lower() not in ("united states", "canada") \
        and not country.lower().startswith("united states")
    if by_name:
        r["state"] = by_name
    elif abroad:
        r["state"] = country              # grouped by country, not a US state
    elif st and st.upper() not in STATE_NAMES and not state_from_zip(r.get("zip")):
        r["state"] = st                   # outside the US, typed as given
    else:
        from_zip = state_from_zip(r.get("zip"))
        two = re.sub(r"[^A-Za-z]", "", st).upper()[:2]
        r["state"] = two if (two and (not from_zip or two == from_zip)) else (from_zip or two)

    # carry a corrected state into the published address line as well
    if st and r["state"] and st.upper() != r["state"] and r.get("address"):
        r["address"] = re.sub(rf",\s*{re.escape(st)}\s+(?={re.escape(str(r.get('zip') or ''))})",
                              f", {r['state']} ", r["address"])

    # a licence field holding only a state name has no number in it
    lic_raw = (r.get("licensure") or "").strip()
    if lic_raw and lic_raw.lower() in NAME_TO_ABBR:
        r["licensure"] = "State licensed — number not provided"

    # web address without a scheme is a broken link
    w = (r.get("website") or "").strip()
    if w and not w.startswith(("http://", "https://")):
        if w.startswith("//"):
            w = "https:" + w
        elif "." in w and " " not in w:
            w = "https://" + w
        r["website"] = w

    # a bare licence number, with no authority named, is not much use
    lic = (r.get("licensure") or "").strip()
    if lic and not re.search(r"board|licen[cs]|college|department|commission|no state",
                             lic, re.I):
        board = None
        for c in r.get("categories", []):
            board = LICENSE_BOARDS.get(c, {}).get(r.get("state", ""))
            if board:
                break
        if board:
            # strip a leading state abbreviation or name the applicant already
            # typed, so we don't end up with "Arizona ... Board #AZ LAC-0001"
            num = lic.strip()
            st = r.get("state", "")
            full = STATE_NAMES.get(st, "") if st else ""
            num = re.sub(rf"^(?:{re.escape(st)}|{re.escape(full)})\b[\s.:#\-]*", "",
                         num, flags=re.I).strip()
            num = num.lstrip("#").strip() or lic
            r["licensure"] = f"{board} #{num}"

    # a name typed inside quotation marks
    nm = (r.get("name") or "").strip()
    if len(nm) > 2 and nm[0] in "\"'\u201c" and nm[-1] in "\"'\u201d":
        r["name"] = nm[1:-1].strip()

    # tidy a phone number typed as a run of digits
    ph = re.sub(r"\D", "", r.get("phone") or "")
    if len(ph) == 11 and ph.startswith("1"):
        ph = ph[1:]
    if len(ph) == 10 and (r.get("phone") or "").strip() != "":
        r["phone"] = f"({ph[:3]}) {ph[3:6]}-{ph[6:]}"
    return r


# Listings written into this file (the original directory), as opposed to ones
# approved through the Worker. Their board checks live in data/verifications.json.
SEED_SLUGS = {p["slug"] for p in PROVIDERS}

def _merge_approved():
    path = os.path.join(ROOT, "data", "listings.json")
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            rows = json.load(f)
    except (ValueError, OSError) as e:
        print(f"  ! data/listings.json unreadable, skipping ({e})")
        return
    have = {p["slug"] for p in PROVIDERS}
    added = 0
    for r in rows:
        if not isinstance(r, dict) or not r.get("slug") or r["slug"] in have:
            continue
        if not r.get("name") or not r.get("categories"):
            print(f"  ! skipping listing {r.get('slug')}: missing name or categories")
            continue
        r["categories"] = [c for c in r["categories"]
                           if any(d["key"] == c for d in DISCIPLINES)]
        if not r["categories"]:
            print(f"  ! skipping listing {r['slug']}: no recognised discipline")
            continue
        for k in ("city", "state"):
            r[k] = (r.get(k) or "").strip()
        if not r["city"] or not r["state"]:
            print(f"  ! skipping listing {r['slug']}: missing city or state")
            continue
        r.setdefault("logo", None)
        r.setdefault("social", [])
        r.setdefault("long", "")
        r.setdefault("verified", False)
        r.setdefault("integrative_training", "")
        r.setdefault("verification", None)
        for k in ("credentials", "licensure", "training", "affiliations",
                  "pricing", "payments", "insurance", "blurb", "address", "zip"):
            r.setdefault(k, "")
        PROVIDERS.append(normalise(r))
        have.add(r["slug"])
        added += 1
    if added:
        print(f"  + {added} listing(s) merged from data/listings.json")

# Admin corrections to approved listings, by slug. Applied on every build.
CORRECTIONS = {
    # Blooming Chiropractic: chiropractic is licensed in California, and the
    # record said the opposite. Credentials taken from their own site (Sep 2026);
    # no licence number is published there, so none is claimed here.
    "blooming-chiropractic": dict(
        person="Dr. Elmira",
        categories=["Chiropractic"],
        credentials="Doctor of Chiropractic (DC) \u00b7 Webster Technique certified",
        licensure="California licensed doctor of chiropractic \u2014 number not provided",
        training="Doctor of Chiropractic; postgraduate prenatal and pediatric coursework with the "
                 "International Chiropractic Pediatric Association (ICPA)",
        pricing=""),
    # Tennessee Neurofeedback: Kaka Ray is an LMFT, which is a licensed
    # discipline, not a coach. Credentials as she reported them (Sep 2026).
    "tennessee-neurofeedback": dict(
        person="Kaka Ray, LMFT",
        categories=["Counseling"],
        credentials="Licensed Marriage and Family Therapist (LMFT) \u00b7 Board Certified in Neurofeedback (BCN), BCIA",
        licensure="Tennessee licensed marriage and family therapist \u2014 number not provided",
        training="Marriage and family therapy; neurofeedback training based on qEEG brain mapping; "
                 "brain-based and trauma-focused methods over 20 years of practice"),
    # Common Roots: RN as well as a licensed TCM practitioner (Sep 2026)
    "common-roots-acupuncture": dict(
        credentials="Registered Nurse (RN) \u00b7 Licensed acupuncturist and practitioner of Chinese medicine",
        licensure="Arizona registered nurse and licensed acupuncturist \u2014 numbers not provided"),
    # Nibodhi Haas ticked every discipline; he is listed for Ayurveda only (Oct 2026)
    "awakened-living": dict(categories=["Ayurveda"]),
    # Lucy asked for her ICF and hypnotherapy credentials to be shown (Sep 2026)
    "coaching-with-lucy": dict(
        credentials="ICF Associate Certified Coach (ACC); Certified Clinical Hypnotherapist (CCHT)"),
}
# Logos supplied by practitioners after listing (Sep 2026), in public/assets/img/providers/
LOGOS = {
    "catalina-acupuncture": "/assets/img/providers/catalina-acupuncture.png",
    "celia-hildebrand-acupuncture": "/assets/img/providers/celia-hildebrand-acupuncture.png",
    "civano-chiropractic-clinics": "/assets/img/providers/civano-chiropractic-clinics.png",
    "emma-vasseur-wellbeing": "/assets/img/providers/emma-vasseur-wellbeing.png",
    "hibiscus-acupuncture": "/assets/img/providers/hibiscus-acupuncture.png",
    "origins-health": "/assets/img/providers/origins-health.png",
    "tracy-villegas-lmt": "/assets/img/providers/tracy-villegas-lmt.jpg",
    # Descending Dragon Health Center (Jarrod Lash), logo sent Oct 2026
    "tucson-manual-and-movement-therapy": "/assets/img/providers/tucson-manual-and-movement-therapy.png",
    "thrive-chiropractic": "/assets/img/providers/thrive-chiropractic.png",
    # submitted as an SVG with a .jpg name, which browsers will not draw (Oct 2026)
    "spectrum-wellcare": "/assets/img/providers/spectrum-wellcare.svg",
}
for _slug, _path in LOGOS.items():
    CORRECTIONS.setdefault(_slug, {})["logo"] = _path

HIDDEN = {
    "test-practice",                                  # never published
    "ayurmantra-ayurveda-holistic-wellness-center",   # India; US and Canada only
}
LISTED_COUNTRIES = {"united states", "canada"}

# A confirmation recorded against the wrong body is withdrawn until re-checked.
# Only the exact bad source is dropped, so a fresh confirmation shows normally.
WRONG_SOURCE = {
    # confirmed against the coaching board while the listing was still
    # mis-tagged as coaching; she is an LMFT (Sep 2026)
    "tennessee-neurofeedback": "the National Board for Health & Wellness Coaching",
    # confirmed against the acupuncture board while the listing was still
    # mis-tagged as acupuncture; she is a chiropractor (Sep 2026)
    "blooming-chiropractic": "the California Acupuncture Board",
    "common-roots-acupuncture": "the American Herbalists Guild",
    "lotus-wellspring-healthcare": "the American Herbalists Guild",
}

def _load_verifications():
    path = os.path.join(ROOT, "data", "verifications.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def _load_overrides():
    """Field edits made from the review page, e.g. corrected disciplines."""
    try:
        with open(os.path.join(ROOT, "data", "overrides.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def _apply_corrections():
    global PROVIDERS
    checks = _load_verifications()
    edits = _load_overrides()        # confirmations recorded for seed listings
    for p in PROVIDERS:
        if isinstance(checks.get(p["slug"]), dict):
            p["verification"] = checks[p["slug"]]
    PROVIDERS[:] = [p for p in PROVIDERS if p["slug"] not in HIDDEN
                    and (p.get("country") or "United States").lower() in LISTED_COUNTRIES]
    for p in PROVIDERS:
        fix = CORRECTIONS.get(p["slug"])
        if fix:
            p.update(fix)
        edit = edits.get(p["slug"])
        if isinstance(edit, dict):
            p.update({k: v for k, v in edit.items() if k != "slug"})
        bad = WRONG_SOURCE.get(p["slug"])
        v = p.get("verification")
        if bad and v and (v.get("source") or "").strip().lower() == bad.lower():
            p["verification"] = None
        # the same text given as both summary and description reads as a mistake
        if (p.get("long") or "").strip() and \
                (p.get("long") or "").strip() == (p.get("blurb") or "").strip():
            p["long"] = ""

_merge_approved()
_apply_corrections()


def _fill_coords():
    """Listings without a street address have no coordinates. Place them at
    their city's centre (from the location-search tables) so a distance
    search still finds them."""
    geo = os.path.join(OUT, "assets", "geo", "places")
    for p in PROVIDERS:
        if p.get("lat") not in (None, "") and p.get("lng") not in (None, ""):
            continue
        city = re.sub(r"\s+", " ", (p.get("city") or "").lower().replace(".", "").replace("'", "")).strip()
        city = re.sub(r"\bsaint\b", "st", city)
        if not city:
            continue
        path = os.path.join(geo, (city[0] if city[0].isalpha() else "0") + ".json")
        try:
            hits = json.load(open(path, encoding="utf-8")).get(city, [])
        except OSError:
            continue
        for region, lat, lng in hits:
            if region == p.get("state"):
                p["lat"], p["lng"] = lat, lng
                break


_fill_coords()

E = html.escape

def disc(key):
    return next(d for d in DISCIPLINES if d["key"] == key)

def cat_count(key):
    return sum(1 for p in PROVIDERS if key in p["categories"])

def state_name(ab):
    return STATE_NAMES.get(ab, ab)

def state_slug(ab):
    return state_name(ab).lower().replace(" ", "-")

STATES = sorted({p["state"] for p in PROVIDERS}, key=state_name)
CITIES = sorted({(p["city"], p["state"]) for p in PROVIDERS})

def in_state(ab):
    return [p for p in PROVIDERS if p["state"] == ab]

def cities_in(ab):
    seen = {}
    for p in in_state(ab):
        c = (p["city"] or "").strip()
        if c and c.lower() not in seen:
            seen[c.lower()] = c.title() if c == c.lower() or c == c.upper() else c
    return sorted(seen.values())

def img_tag(url, alt, sizes, cls="", widths=(500, 750, 1000, 1500), lazy=True):
    """A remote URL gets Squarespace's ?format= resize parameter. A local stem
    like /assets/img/disciplines/integrative expands to the generated sizes,
    with a WebP source and a content hash for cache-busting."""
    if not url:
        return ""
    if url.startswith("/"):
        lz = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
        c = f' class="{cls}"' if cls else ""
        ws = [w for w in widths if w <= 1000] or [1000]
        def sset(ext):
            return ", ".join(
                f'{url}-{w}.{ext}?v={_v(f"{url}-{w}.{ext}".lstrip("/"))} {w}w' for w in ws)
        mid = ws[len(ws) // 2]
        return (f'<picture><source type="image/webp" srcset="{sset("webp")}" sizes="{sizes}">'
                f'<img{c} src="{url}-{mid}.jpg?v={_v(f"{url}-{mid}.jpg".lstrip("/"))}" '
                f'srcset="{sset("jpg")}" sizes="{sizes}" alt="{E(alt)}"{lz}></picture>')
    ss = ", ".join(f"{url}?format={w}w {w}w" for w in widths)
    lz = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    c = f' class="{cls}"' if cls else ""
    return (f'<img{c} src="{url}?format={widths[-1]}w" srcset="{ss}" '
            f'sizes="{sizes}" alt="{E(alt)}"{lz}>')

LOGO = IMG["logo"]

# Social share card, 1200x630, built by make_card.py.
CARD_V = _v("assets/img/share-card.jpg")

# The lockup, hosted locally. 3.34:1, so a 72px tall header logo is ~240px wide.
LOGO_V = _v("assets/img/logo-800.png")
LOGO_MARKUP = f"""<img src="/assets/img/logo-800.png?v={LOGO_V}"
           srcset="/assets/img/logo-400.png?v={_v("assets/img/logo-400.png")} 400w, /assets/img/logo-800.png?v={LOGO_V} 800w"
           sizes="(max-width:900px) 190px, 280px" width="965" height="289"
           alt="FindWell Directory — a network of holistic health care providers">"""

# Favicons built from the logo's graphic mark by make_favicon.py. Until that
# script has been run against the real logo, fall back to the full logo file.
if os.path.exists(os.path.join(OUT, "assets/img/favicon.png")):
    _fv = _v("assets/img/favicon.png")
    FAVICON_TAGS = (
        f'<link rel="icon" type="image/png" sizes="32x32" href="/assets/img/favicon-32.png?v={_v("assets/img/favicon-32.png")}">\n'
        f'<link rel="icon" type="image/png" sizes="512x512" href="/assets/img/favicon.png?v={_fv}">\n'
        f'<link rel="apple-touch-icon" href="/assets/img/favicon-180.png?v={_v("assets/img/favicon-180.png")}">\n'
        f'<link rel="shortcut icon" href="/assets/img/favicon.ico?v={_v("assets/img/favicon.ico")}">'
    )
else:
    FAVICON_TAGS = (
        f'<link rel="icon" type="image/png" href="{LOGO}?format=300w">\n'
        f'<link rel="apple-touch-icon" href="{LOGO}?format=500w">'
    )

# Hero photograph, hosted locally in /assets/img (not hotlinked).
# Regenerate the sizes with make_hero.py if the source image changes.
HERO = f"""<picture>
      <source type="image/webp" sizes="100vw"
              srcset="/assets/img/hero-900.webp?v={IMG_V} 900w, /assets/img/hero-1400.webp?v={IMG_V} 1400w, /assets/img/hero-2000.webp?v={IMG_V} 2000w">
      <img class="hero-bg" src="/assets/img/hero-1400.jpg?v={IMG_V}" sizes="100vw"
           srcset="/assets/img/hero-900.jpg?v={IMG_V} 900w, /assets/img/hero-1400.jpg?v={IMG_V} 1400w, /assets/img/hero-2000.jpg?v={IMG_V} 2000w"
           width="2000" height="1250" alt="" aria-hidden="true" fetchpriority="high">
    </picture>"""

# ---------------------------------------------------------------------------
# Botanical line drawings, used as quiet decoration (Oct 2026 redesign).
LEAF_MARK = ('<svg width="34" height="34" viewBox="0 0 40 40" fill="none" aria-hidden="true">'
             '<path d="M20 36C20 24 22 14 32 6C34 18 30 30 20 36Z" fill="#7f9a6c"/>'
             '<path d="M20 36C20 26 17 18 8 12C7 24 11 32 20 36Z" fill="#2f4a35"/></svg>')
LEAF_VEIN = ('<svg viewBox="0 0 200 320" fill="none" stroke="currentColor" stroke-width="0.8" stroke-linecap="round" aria-hidden="true">'
             '<path d="M100 312C100 220 100 120 100 12"/>'
             '<path d="M100 30C58 62 30 122 40 200C48 258 88 298 100 312C112 298 152 258 160 200C170 122 142 62 100 30Z"/>'
             '<path d="M100 80C84 90 70 104 60 122M100 120C80 132 62 150 50 172M100 160C82 172 66 190 56 214M100 200C86 212 74 228 68 248'
             'M100 80C116 90 130 104 140 122M100 120C120 132 138 150 150 172M100 160C118 172 134 190 144 214M100 200C114 212 126 228 132 248"/></svg>')
SPRIG = ('<svg viewBox="0 0 60 100" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" aria-hidden="true">'
         '<path d="M30 98C30 70 32 40 40 4"/><path d="M31 80C22 76 16 70 14 60C22 60 28 66 31 80Z"/>'
         '<path d="M32 62C40 60 46 54 48 44C40 44 34 50 32 62Z"/><path d="M33 44C25 40 20 34 19 24C27 25 32 32 33 44Z"/>'
         '<path d="M36 26C42 23 46 17 46 9C40 11 36 17 36 26Z"/></svg>')
SPRIG_SMALL = ('<svg class="fw-ico" width="40" height="56" viewBox="0 0 60 100" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true">'
               '<path d="M30 98C30 70 32 40 40 4"/><path d="M31 80C22 76 16 70 14 60C22 60 28 66 31 80Z"/>'
               '<path d="M32 62C40 60 46 54 48 44C40 44 34 50 32 62Z"/><path d="M33 44C25 40 20 34 19 24C27 25 32 32 33 44Z"/></svg>')
LEAF_PAIR = ('<svg class="fw-ico" width="40" height="56" viewBox="0 0 60 100" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true">'
             '<path d="M30 98C30 60 30 30 30 6"/><path d="M30 60C18 50 14 36 16 22C26 30 30 44 30 60Z"/>'
             '<path d="M30 60C42 50 46 36 44 22C34 30 30 44 30 60Z"/></svg>')
BUD = ('<svg class="fw-ico" width="40" height="56" viewBox="0 0 60 100" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true">'
       '<circle cx="30" cy="30" r="16"/><path d="M30 46V98M30 70C22 66 16 60 14 52M30 80C38 76 44 70 46 62"/></svg>')
LEAF_ICON = ('<svg class="fw-leaf-ic" width="30" height="30" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
             '<path d="M5 19C5 11 10 5 20 4C20 13 14 19 5 19Z"/></svg>')
def _ic(path):
    return ('<svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>')
DISC_ICONS = {
    "Acupuncture": _ic('<path d="M12 21V4"/><circle cx="12" cy="4" r="1.6"/>'),
    "TCM": SPRIG_SMALL, "Naturopathy": LEAF_PAIR, "Herbalism": BUD,
    "Counseling": _ic('<path d="M4 12h3l3-7 4 14 3-7h3"/>'),
    "Bodywork": _ic('<path d="M7 11V6a2 2 0 0 1 4 0v5M11 10V5a2 2 0 0 1 4 0v6M15 10a2 2 0 0 1 4 0v3a8 8 0 0 1-8 8 7 7 0 0 1-6-4l-2-4a2 2 0 0 1 3-2l2 2"/>'),
    "EnergyMedicine": _ic('<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2"/>'),
    "Chiropractic": _ic('<path d="M12 3v18M8 7h8M7 12h10M8 17h8"/>'),
    "Farms": _ic('<path d="M3 20h18M6 20V10l6-5 6 5v10"/>'),
    "Grocers": _ic('<path d="M4 7h16l-1.5 11a2 2 0 0 1-2 1.7h-9a2 2 0 0 1-2-1.7Z"/><path d="M9 7a3 3 0 0 1 6 0"/>'),
}
# Friendlier names for the disciplines, used wherever a reader sees them.
FRIENDLY = {"Ayurveda": "Ayurveda", "Acupuncture": "Acupuncture", "TCM": "Chinese medicine",
            "Naturopathy": "Naturopathic doctors", "IntegrativeMedicine": "Integrative medicine",
            "Counseling": "Counseling", "Coaching": "Health coaching", "Nutrition": "Nutrition",
            "Massage": "Massage", "Bodywork": "Body work", "EnergyMedicine": "Energy work",
            "Chiropractic": "Chiropractic", "Herbalism": "Herbal medicine",
            "Farms": "Local farms", "Grocers": "Local grocers"}
def friendly(key):
    return FRIENDLY.get(key) or next((d["label"] for d in DISCIPLINES if d["key"] == key), key)
DISC_BLURBS = {"Ayurveda": "training and certification shown", "Acupuncture": "licensed acupuncturists",
               "TCM": "herbs, tuina and qigong", "Naturopathy": "licensed ND or NMD",
               "IntegrativeMedicine": "MD, DO, NP, PA and RN", "Counseling": "licensed therapists",
               "Coaching": "board-certified coaches", "Nutrition": "dietitians and nutritionists",
               "Massage": "licensed massage therapists", "Bodywork": "craniosacral, tuina and more",
               "EnergyMedicine": "Reiki and biofield therapies", "Chiropractic": "licensed doctors of chiropractic",
               "Herbalism": "herbalists and educators", "Farms": "growers and CSAs", "Grocers": "local and co-op stores"}

# ---------------------------------------------------------------------------
# A line drawing for each page banner, in the same hand as the plants. viewBox 0 0 240 240, stroke only.
_DLEAF = lambda x, y, r=0, s=1: (f'<g transform="translate({x} {y}) rotate({r}) scale({s})">'
                               '<path d="M0 0C-10-14-10-34 0-48C10-34 10-14 0 0Z"/><path d="M0 0V-44"/></g>')

def _dsprig(x, y, r=0, s=1):
    return (f'<g transform="translate({x} {y}) rotate({r}) scale({s})">'
            '<path d="M0 0C0-22 2-44 8-64"/>'
            '<path d="M1-16C-8-19-14-25-16-34C-8-34-2-28 1-16Z"/>'
            '<path d="M3-32C12-34 18-40 20-50C12-50 6-44 3-32Z"/>'
            '<path d="M5-48C-2-51-7-57-8-65C-1-64 4-58 5-48Z"/></g>')

DRAWINGS = {
  # Find care: a magnifying glass with a sprig growing inside the lens
  "find": '<circle cx="100" cy="98" r="58"/><circle cx="100" cy="98" r="50" opacity=".5"/>'
          '<path d="M142 140L196 194M150 132L204 186M196 194C200 198 206 198 208 194C212 190 210 186 204 186"/>'
          + _dsprig(96, 136, 0, 1.15),
  # Disciplines: a bundle of herbs tied with twine
  "bundle": '<path d="M120 212C118 170 112 120 92 70M120 212C121 166 122 112 124 56M120 212C124 168 134 120 156 76"/>'
            + _DLEAF(92, 74, -30, .9) + _DLEAF(80, 104, -60, .7) + _DLEAF(124, 60, 0, 1) + _DLEAF(110, 96, -40, .7)
            + _DLEAF(156, 80, 30, .9) + _DLEAF(140, 108, 55, .7)
            + '<path d="M106 170C114 176 128 176 136 170M106 178C114 184 128 184 136 178"/>'
              '<path d="M136 174C150 172 160 180 156 190M106 174C94 176 88 186 94 194"/>',
  # Ayurveda and herbal medicine: mortar and pestle with herbs
  "mortar": '<path d="M44 128H196C196 172 164 200 120 200C76 200 44 172 44 128Z"/><path d="M40 128H200"/>'
            '<path d="M92 200L86 214H154L148 200"/>'
            '<path d="M150 56L170 44C176 40 184 46 180 52L134 128"/>'
            + _dsprig(68, 128, -18, .9) + _DLEAF(98, 128, 10, .6),
  # Locations: a saguaro under mountains, with a map pin
  "desert": '<path d="M20 168L70 112L98 140L132 96L184 152L220 128"/>'
            '<path d="M150 210V120C150 112 162 112 162 120V210M150 170H138C132 170 130 166 130 160V140C130 134 138 134 138 140V158H150M162 156H172V132C172 126 180 126 180 132V156C180 164 176 168 170 168H162"/>'
            '<path d="M14 210H226"/>'
            '<path d="M70 70C70 54 82 44 94 44C106 44 118 54 118 70C118 90 94 112 94 112C94 112 70 90 70 70Z"/><circle cx="94" cy="70" r="9"/>',
  # How we verify: a leaf with a check mark
  "verify": '<path d="M120 214C120 150 120 90 120 26"/>'
            '<path d="M120 40C72 74 46 128 58 182C66 204 98 214 120 214C142 214 174 204 182 182C194 128 168 74 120 40Z"/>'
            '<path d="M120 90C104 98 92 110 84 126M120 130C102 138 88 152 80 168M120 90C136 98 148 110 156 126"/>'
            '<circle cx="168" cy="166" r="30"/><path d="M154 166L164 176L184 154"/>',
  # About us: a young plant unfurling from the ground
  "hands": '<path d="M96 238C104 230 136 230 144 238"/>'
           '<path d="M120 236C118 200 122 160 120 112C119 92 124 76 134 66"/>'
           '<path d="M120 176C96 178 74 166 64 142C88 138 112 150 120 176Z"/><path d="M120 176C108 164 92 156 74 150"/>'
           '<path d="M121 150C144 150 164 136 172 112C148 110 126 124 121 150Z"/><path d="M121 150C134 138 150 128 166 118"/>'
           '<path d="M134 66C124 58 120 46 124 34C136 40 140 54 134 66Z"/><path d="M134 66C142 58 154 56 162 60C156 70 144 72 134 66Z"/>',
  # Articles: an open book with a sprig rising from the spine
  "book": '<path d="M120 176C96 162 64 158 30 164V68C64 62 96 66 120 80C144 66 176 62 210 68V164C176 158 144 162 120 176Z"/>'
          '<path d="M120 80V176"/><path d="M50 92C70 88 90 90 106 98M50 112C70 108 90 110 106 118M134 98C150 90 170 88 190 92M134 118C150 110 170 108 190 112"/>'
          + _dsprig(120, 78, 0, .95),
  # Advertise: a flowering branch
  "branch": '<path d="M24 200C70 176 112 140 140 96C156 72 176 54 204 44"/>'
            '<path d="M92 158C86 140 90 124 102 114M140 96C150 112 166 118 182 114"/>'
            + _DLEAF(70, 180, -110, .7) + _DLEAF(118, 132, -150, .6) + _DLEAF(170, 66, 60, .6)
            + ''.join(f'<g transform="translate({x} {y})"><circle r="6"/>'
                      + ''.join(f'<ellipse rx="7" ry="12" transform="rotate({a}) translate(0 -14)"/>' for a in (0, 72, 144, 216, 288))
                      + '</g>' for x, y in ((102, 108), (186, 108), (206, 40))),
  # List your practice: a watering can and a sprout
  "join": '<path d="M40 110H128V176C128 186 120 192 110 192H58C48 192 40 186 40 176Z"/>'
          '<path d="M128 132L176 96L182 104L128 148"/><path d="M174 90L188 108"/><path d="M60 110C60 82 108 82 108 110"/>'
          '<path d="M186 114V118M194 124V130M180 128V134"/>'
          '<path d="M164 212H220M176 212L172 188H212L208 212"/><path d="M192 188V162"/>'
          '<path d="M192 172C182 172 174 164 172 154C182 154 190 162 192 172Z"/><path d="M192 166C202 166 210 158 212 148C202 148 194 156 192 166Z"/>',
  # Not found: a fallen leaf by a winding path
  "lost": '<path d="M20 214C70 200 60 170 110 160C160 150 150 120 210 110" stroke-dasharray="2 9"/>'
          '<g transform="translate(120 96) rotate(-60)"><path d="M0 60C-30 30-30-20 0-60C30-20 30 30 0 60Z"/><path d="M0 70V-56M0-10L-16-26M0 10L16-6M0 30L-14 16"/></g>',
  # Acupuncture: three fine needles above a lotus
  "needles": '<path d="M84 40L100 140M120 30V140M156 40L140 140"/><circle cx="84" cy="36" r="5"/><circle cx="120" cy="26" r="5"/><circle cx="156" cy="36" r="5"/>'
             '<path d="M120 200C104 184 104 164 120 150C136 164 136 184 120 200Z"/>'
             '<path d="M120 200C98 196 84 180 84 160C104 162 116 178 120 200Z"/><path d="M120 200C142 196 156 180 156 160C136 162 124 178 120 200Z"/>'
             '<path d="M120 200C92 204 66 194 54 176C78 172 104 182 120 200Z"/><path d="M120 200C148 204 174 194 186 176C162 172 136 182 120 200Z"/>',
  # Chinese medicine: a ginseng root with leaves
  "root": '<path d="M120 120C108 140 106 162 112 184C116 196 110 208 98 216M118 160C104 168 92 182 86 200M124 150C140 160 150 176 154 196M114 186C126 194 132 206 132 218"/>'
          '<path d="M120 120V40"/>' + _DLEAF(120, 74, -50, 1) + _DLEAF(120, 74, 50, 1) + _DLEAF(120, 74, 0, 1.1)
          + '<circle cx="120" cy="34" r="4"/><circle cx="112" cy="40" r="4"/><circle cx="128" cy="40" r="4"/>',
  # Nutrition: a bowl of fruit and greens
  "bowl": '<path d="M36 128H204C204 174 168 200 120 200C72 200 36 174 36 128Z"/><path d="M96 200L92 212H148L144 200"/>'
          '<circle cx="84" cy="112" r="16"/><circle cx="116" cy="106" r="20"/><circle cx="154" cy="114" r="14"/>'
          '<path d="M116 86C116 76 120 68 128 62"/>' + _DLEAF(130, 62, 50, .6) + _DLEAF(70, 126, -55, .7) + _DLEAF(176, 126, 55, .7),
  # Massage and body work: stacked smooth stones with a leaf
  "stones": '<ellipse cx="120" cy="196" rx="74" ry="18"/><ellipse cx="120" cy="164" rx="56" ry="15"/>'
            '<ellipse cx="120" cy="136" rx="40" ry="12"/><ellipse cx="120" cy="113" rx="26" ry="10"/>'
            + _dsprig(120, 104, 8, 1.05),
  # Integrative medicine, naturopathy, counseling: a heart of two leaves
  "heart": '<path d="M120 204C82 176 44 144 44 104C44 76 64 56 88 56C104 56 116 66 120 80C124 66 136 56 152 56C176 56 196 76 196 104C196 144 158 176 120 204Z"/>'
           '<path d="M120 80V200M120 110C104 104 90 94 80 80M120 140C100 132 84 118 72 104M120 110C136 104 150 94 160 80M120 140C140 132 156 118 168 104"/>',
  # Energy work: a sun over a sprouting leaf
  "sun": '<circle cx="120" cy="92" r="32"/>'
         + ''.join(f'<path d="M120 46V30" transform="rotate({a} 120 92)"/>' for a in range(0, 360, 30))
         + '<path d="M120 214V160"/><path d="M120 180C102 180 90 168 88 150C106 150 118 162 120 180Z"/><path d="M120 170C138 170 150 158 152 140C134 140 122 152 120 170Z"/><path d="M60 214H180"/>',
  # Chiropractic: a fern frond, like a gentle spine
  "fern": '<path d="M120 222C116 160 122 90 120 18"/>' + ''.join(
          f'<path d="M120 {y}C{120-w} {y-6} {120-w*1.6} {y-4} {120-w*2} {y+2}C{120-w*1.6} {y+8} {120-w} {y+6} 120 {y}Z"/>'
          f'<path d="M120 {y-12}C{120+w} {y-18} {120+w*1.6} {y-16} {120+w*2} {y-10}C{120+w*1.6} {y-4} {120+w} {y-6} 120 {y-12}Z"/>'
          for y, w in ((200, 26), (172, 24), (144, 21), (116, 18), (88, 14), (60, 10), (36, 6))),
  # Health coaching: a winding path toward a rising sun
  "path": '<path d="M70 214C90 180 150 176 140 150C130 126 92 130 104 108C112 94 128 92 132 84"/>'
          '<path d="M150 214C160 186 186 176 172 150C160 128 124 130 128 110C130 100 134 94 136 84"/>'
          '<path d="M60 84H180"/><path d="M96 84C96 64 108 52 120 52C132 52 144 64 144 84"/>'
          + ''.join(f'<path d="M120 42V32" transform="rotate({a} 120 84)"/>' for a in (-60, -30, 0, 30, 60))
          + _dsprig(56, 214, -10, .8) + _dsprig(188, 214, 12, .8),
  # Local farms and grocers: a basket of vegetables
  "basket": '<path d="M44 120H196L182 202H58Z"/><path d="M50 150H190M54 178H186M88 120L94 202M120 120V202M152 120L146 202"/>'
            '<path d="M70 120C70 70 170 70 170 120"/>'
            '<path d="M96 120L84 76L108 112"/><path d="M84 76C76 66 78 54 86 50M84 76C90 64 100 60 106 62"/>'
            '<circle cx="138" cy="104" r="16"/><path d="M138 88C138 80 142 74 148 72"/>' + _DLEAF(150, 72, 60, .5),
}

DRAW_BASE = {"find": 200, "bundle": 214, "mortar": 216, "desert": 211, "verify": 216, "hands": 239,
             "book": 196, "branch": 204, "join": 213, "lost": 216, "needles": 206, "root": 220,
             "bowl": 214, "stones": 216, "heart": 206, "sun": 215, "fern": 223, "path": 215, "basket": 204}

def drawing(key, cls="pg-art"):
    vy = DRAW_BASE.get(key, 240) - 240
    return (f'<svg class="{cls}" viewBox="0 {vy} 240 240" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{DRAWINGS[key]}</svg>')


GROUND_SPRIGS = "".join(
    f'<svg class="pg-sprig" style="left:{x}%;width:{w}px;height:{round(w * 1.66)}px;transform:rotate({r}deg);opacity:{o}" '
    'viewBox="0 0 60 100" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round">'
    '<path d="M30 98C30 70 32 40 40 4"/><path d="M31 80C22 76 16 70 14 60C22 60 28 66 31 80Z"/>'
    '<path d="M32 62C40 60 46 54 48 44C40 44 34 50 32 62Z"/><path d="M33 44C25 40 20 34 19 24C27 25 32 32 33 44Z"/></svg>'
    for x, w, r, o in ((2, 46, -6, .45), (41, 58, -8, .7), (48.5, 40, 10, .5), (93, 66, 6, .6)))

DISC_DRAWING = {"Ayurveda": "mortar", "Herbalism": "mortar", "Acupuncture": "needles", "TCM": "root",
                "Naturopathy": "bundle", "IntegrativeMedicine": "heart", "Counseling": "hands",
                "Coaching": "path", "Nutrition": "bowl", "Massage": "stones", "Bodywork": "stones",
                "EnergyMedicine": "sun", "Chiropractic": "fern", "Farms": "basket", "Grocers": "basket"}

def shell(title, desc, path, body, view="", extra_head=""):
    """Wrap page content in the shared chrome. `path` is the canonical URL path."""
    links = [("/directory/", "Find care"), ("/locations/", "Locations"), ("/practice-types/", "Disciplines"),
             ("/verification/", "How we verify"), ("/about/", "About us"),
             ("/articles/", "Articles")]
    def cur(h):
        hit = path.startswith(h) or (h == "/directory/" and path.startswith("/provider/"))
        return ' aria-current="page"' if hit else ""
    navhtml = "".join(f'<a href="{h}"{cur(h)}>{t}</a>' for h, t in links)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{SITE}{path}">
{FAVICON_TAGS}
<meta property="og:site_name" content="FindWell Directory">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:image" content="{SITE}/assets/img/share-card.jpg?v={CARD_V}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="FindWell Directory: licensure, training, years in practice and pricing on every listing.">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE}/assets/img/share-card.jpg?v={CARD_V}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Young+Serif&family=Figtree:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css?v={CSS_V}">
{extra_head}
</head>
<body{f' data-view="{view}"' if view else ''}>
<a class="skip" href="#main">Skip to content</a>

<header class="masthead">
  <div class="wrap masthead-in">
    <a class="mark" href="/" aria-label="FindWell Directory, home">{LOGO_MARKUP}</a>
    <button class="burger" id="burger" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav class="nav" id="nav" aria-label="Main">
      {navhtml}
      <a class="cta" href="/join/">List your practice</a>
    </nav>
  </div>
</header>

<main id="main">
{body}
</main>

<footer class="foot">
  <div class="wrap foot-in">
    <div class="foot-about">
      <span class="foot-mark"><img src="/assets/img/logo-400.png?v={_v("assets/img/logo-400.png")}" width="965" height="289" alt="FindWell Directory" loading="lazy" decoding="async"></span>
      <p>A free directory of holistic and integrative practitioners in the United States and Canada. No commissions, no listing fees, no lead selling.</p>
    </div>
    <div class="foot-col">
      <a href="/directory/">Find care</a>
      <a href="/practice-types/">Disciplines</a>
      <a href="/locations/">Locations</a>
      <a href="/verification/">How we verify</a>
      <a href="/articles/">Articles</a>
    </div>
    <div class="foot-col">
      <a href="/join/">List your practice</a>
      <a href="/about/">About us</a>
      <a href="/advertise/">Advertise with us</a>
      <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
    </div>
  </div>
  <div class="wrap foot-legal">&copy; {YEAR} FindWell Directory. Listings are informational and are not a referral, endorsement or medical advice.</div>
</footer>
<script src="/assets/app.js?v={JS_V}" defer></script>
</body>
</html>
"""



# ---------------------------------------------------------------------------
def console_html():
    chips = "".join(
        f'<button type="button" class="chip" data-chip="{d["key"]}">{E(d["label"])}'
        f'<span class="n">{cat_count(d["key"])}</span></button>'
        for d in DISCIPLINES if cat_count(d["key"]))
    whereopts = "".join(f'<option value="{E(state_name(ab))}">' for ab in STATES)
    return f"""<form class="console" id="console" action="/directory/" method="get">
    <div class="console-hd">
      <h2>Search the directory</h2>
      <p class="console-count">{len(PROVIDERS)} practitioners listed</p>
    </div>
    <div class="console-grid">
      <div class="field">
        <label for="c-q">What are you looking for</label>
        <input class="control" id="c-q" name="q" type="search" placeholder="Ayurveda, acupuncture, a name…">
      </div>
      <div class="field">
        <label for="c-loc">Where</label>
        <input class="control" id="c-loc" name="where" type="text" placeholder="State or ZIP code" list="where-list">
        <datalist id="where-list">{whereopts}</datalist>
      </div>
      <button class="btn btn-primary" type="submit">Search</button>
    </div>
    <div class="chips" role="group" aria-label="Filter by discipline">{chips}
      <button type="button" class="chip" data-near="1">Use my location</button>
    </div>
  </form>"""

def remote_label(p):
    """What a listing's remote care is called. Most say Telehealth; a
    practice can ask for its own wording (e.g. Distance Reiki)."""
    return (p.get("remote_label") or "Telehealth").strip()

def tags_html(p):
    t = "".join(f'<a class="tag" href="/practice-types/{disc(c)["slug"]}/">{E(friendly(c))}</a>'
                for c in p["categories"])
    if p["telehealth"]:
        t += f'<span class="tag tag-tele">{E(remote_label(p))}</span>'
    return f'<div class="record-tags">{t}</div>'

def initials(name):
    parts = [w for w in "".join(ch for ch in name if ch.isalpha() or ch == " ").split() if w]
    return "".join(w[0].upper() for w in parts[:2])

def avatar(p, big=False):
    """Provider logo. A local path (starting with /) is served from our own
    assets with a cache-busting hash, and a WebP variant is used when one
    exists. A remote URL gets Squarespace's resize parameter instead."""
    cls = "avatar avatar-lg" if big else "avatar"
    logo = p["logo"]
    if not logo:
        return f'<div class="{cls} avatar-mono" aria-hidden="true">{E(initials(p["name"]))}</div>'
    if not logo.startswith("/"):
        return f'<img class="{cls}" src="{logo}?format=500w" alt="{E(p["name"])} logo" loading="lazy" decoding="async">'
    rel = logo.lstrip("/")
    full = os.path.join(OUT, rel)
    if not os.path.exists(full) or os.path.getsize(full) < 100:
        # empty or missing file — show the monogram rather than a broken image
        return f'<div class="{cls} avatar-mono" aria-hidden="true">{E(initials(p["name"]))}</div>'
    src = f'{logo}?v={_v(rel)}'
    webp = logo.rsplit(".", 1)[0] + ".webp"
    img = (f'<img class="{cls}" src="{src}" alt="{E(p["name"])} logo" '
           f'loading="lazy" decoding="async" width="200" height="200">')
    if os.path.exists(os.path.join(OUT, webp.lstrip("/"))):
        return (f'<picture><source type="image/webp" srcset="{webp}?v={_v(webp.lstrip("/"))}">'
                f'{img}</picture>')
    return img

def verification_line(p):
    """Two honest states, never a badge that overstates.

    Either we checked with the issuing authority and say so with the source and
    date, or the practitioner told us and we say that instead. "Not yet
    verified" is avoided deliberately: on FindWell, unverified is a permanent
    and acceptable state, not a backlog.
    """
    v = p.get("verification")
    if v and v.get("source"):
        when = v.get("date", "")
        # the line always opens the same way, so a reader never has to work out
        # whether a licence number at the front means confirmed or claimed
        what = (v.get("what") or "").strip()
        detail = "" if re.match(r"(?i)^credentials? confirmed\b", what) else what
        return (f'<p class="verify verify-confirmed">'
                f'<b>Credentials confirmed</b>'
                f'{": " + E(detail) if detail else ""} with {E(v["source"])}'
                f'{", " + E(when) if when else ""}.</p>')
    return ('<p class="verify verify-reported">'
            '<b>As reported by the practitioner.</b> Not independently verified \u2014 '
            '<a href="/verification/">what this means</a>.</p>')

def integrative_row(p):
    """Shown for integrative and functional medicine listings. An empty value
    is published as 'None reported' rather than being left off the record."""
    if "IntegrativeMedicine" not in p["categories"]:
        return ""
    v = (p.get("integrative_training") or "").strip()
    return (f'<dt>Integrative training</dt>'
            f'<dd{"" if v else " class=\"na\""}>{E(v) if v else "None reported"}</dd>')

def years_text(p, word="yrs"):
    """A listing with no usable start year still has to render."""
    since = p.get("since")
    try:
        since = int(since)
    except (TypeError, ValueError):
        return "—"
    if not (1900 < since <= YEAR):
        return "—"
    return f"{YEAR - since} {word} (since {since})"

def val(x, dash="—"):
    """Never render an empty cell. A dash says 'nothing was given'; a blank
    space looks like the page is broken."""
    x = (x or "").strip()
    return E(x) if x else dash

def record_html(p):
    hay = " ".join([p["name"], p["person"], p["city"], p["state"], p["zip"],
                    p["credentials"], p["training"], p["blurb"], p["licensure"]] +
                   [disc(c)["label"] for c in p["categories"]] +
                   [friendly(c) for c in p["categories"]]).lower()
    fee = fee_from(p)
    meta = " · ".join(x for x in [E(p["person"]) if p["person"] and p["person"] != p["name"] else "",
                                         f'{E(p["city"])}, {E(p["state"])}', since_txt(p)] if x)
    return f"""<li class="record" data-cats="{' '.join(p['categories'])}"
      data-city="{E(p['city'])}" data-state="{p['state']}" data-tele="{1 if p['telehealth'] else 0}"
      data-lat="{p['lat'] if p['lat'] is not None else ''}" data-lng="{p['lng'] if p['lng'] is not None else ''}" data-since="{p['since']}"
      data-name="{E(p['name'])}" data-text="{E(hay)}">
    <article class="rec">
      {avatar(p)}
      <div class="rec-body">
        <h3 class="record-name"><a href="/provider/{p['slug']}/">{E(p['name'])}</a></h3>
        <p class="rec-meta">{meta} <span class="record-dist"></span></p>
        <p class="rec-blurb">{E((p.get('blurb') or '')[:170])}{'…' if len(p.get('blurb') or '') > 170 else ''}</p>
        <div class="fw-tags">{chips_html(p, 3)}{verify_tag(p)}</div>
      </div>
      {f'<div class="rec-fee"><span class="rec-fee-n">{E(fee)}</span><span class="rec-fee-l">from</span></div>' if fee else ''}
    </article>
  </li>"""



# ---------------------------------------------------------------------------
# Direction A (Oct 2026): practitioner-forward home and listing pages.

def _has_logo(p):
    logo = p.get("logo") or ""
    if not logo:
        return False
    if not logo.startswith("/"):
        return True
    full = os.path.join(OUT, logo.lstrip("/"))
    return os.path.exists(full) and os.path.getsize(full) >= 100

def labels_html(p, cls="ha-chip"):
    """Discipline labels as plain text, for use inside a card that is itself a link."""
    t = "".join(f'<span class="{cls}">{E(disc(c)["label"])}</span>' for c in p["categories"])
    if p["telehealth"]:
        t += f'<span class="{cls} {cls}-tele">{E(remote_label(p))}</span>'
    return t

def verify_short(p):
    """One line for a card. Never claims more than the full listing does."""
    v = p.get("verification")
    if v and v.get("source"):
        src = re.sub(r"(?i)^the\s+", "", v["source"]).split(",")[0]
        return ('<span class="ha-ok"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
                'stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" '
                f'aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>Confirmed with {E(src)}</span>')
    if re.search(r"(?i)no state licensure", p.get("licensure") or ""):
        return '<span class="ha-note">No state licensure exists &middot; training shown</span>'
    return '<span class="ha-note">Credentials as reported by the practitioner</span>'

def card_html(p):
    since = p.get("since")
    try:
        since_txt = f"Since {int(since)}" if 1900 < int(since) <= YEAR else ""
    except (TypeError, ValueError):
        since_txt = ""
    return f"""<a class="ha-card" href="/provider/{p['slug']}/">
        <div class="ha-card-head">{avatar(p)}<div class="ha-card-id">
          <span class="ha-card-name">{E(p['name'])}</span>
          <span class="ha-card-person">{E(p['person'])}</span></div></div>
        <div class="ha-chips">{labels_html(p)}</div>
        <div class="ha-card-meta"><span>{E(p['city'])}, {E(p['state'])}</span><span>{since_txt}</span></div>
        <div class="ha-card-verify">{verify_short(p)}</div>
      </a>"""

def fee_items(p):
    """The fee text split into lines a reader can scan."""
    raw = (p.get("pricing") or "").strip()
    if raw in ("", ".", "—", "-"):
        return []
    parts = re.split(r"\s*·\s*|\r?\n+", raw)
    return [x.strip() for x in parts if x.strip()]

def _featured():
    """The hero card: a confirmed listing with a logo, most recently checked."""
    def tidy(p):
        f = fee_items(p)
        return bool(f) and len(f[0]) <= 48 and not re.search(r"(?i)no state licensure", p.get("licensure") or "")
    pool = [p for p in PROVIDERS if _has_logo(p) and (p.get("verification") or {}).get("source")]
    pool.sort(key=lambda p: (tidy(p), p["verification"].get("recorded_at") or ""), reverse=True)
    return pool[0] if pool else (PROVIDERS[0] if PROVIDERS else None)

HERO_FIGURE = f"""<picture>
      <source type="image/webp" sizes="(max-width:900px) 100vw, 560px"
              srcset="/assets/img/hero-900.webp?v={IMG_V} 900w, /assets/img/hero-1400.webp?v={IMG_V} 1400w">
      <img class="ha-hero-img" src="/assets/img/hero-1400.jpg?v={IMG_V}" sizes="(max-width:900px) 100vw, 560px"
           srcset="/assets/img/hero-900.jpg?v={IMG_V} 900w, /assets/img/hero-1400.jpg?v={IMG_V} 1400w"
           width="1400" height="875" alt="A practitioner smiling in a sunlit practice room" fetchpriority="high">
    </picture>"""

def page_head(h1, lede="", trail=None, h1_html=None, art=None):
    """The sage band at the top of every inner page: crumbs, heading, a line of
    introduction, and a faint leaf drawing."""
    crumbs = crumbs_html(trail) if trail else ""
    return f"""  <section class="pg-head">
    <div class="pg-ground" aria-hidden="true">{GROUND_SPRIGS}</div>
    <div class="wrap pg-head-in{' pg-has-art' if art else ''}">
      {f'<span class="pg-art-wrap">{drawing(art)}</span>' if art else ''}
      {crumbs}
      <h1>{h1_html or E(h1)}</h1>
      {f'<p class="pg-lede">{lede}</p>' if lede else ''}
    </div>
  </section>"""


def verify_tag(p):
    """Short honey-coloured tag for cards. Nothing at all when unconfirmed."""
    v = p.get("verification")
    if not (v and v.get("source")):
        return ""
    src = v["source"]
    lic = re.search(r"(?i)board of (examiners|chiropractic|medicine|nursing|behavioral|registration|osteopathic)|"
                    r"acupuncture board|massage therapy board|department of health|dca licen|medical board|"
                    r"naturopathic physicians", src)
    return f'<span class="fw-tag fw-tag-ok">{"License confirmed" if lic else "Credentials confirmed"}</span>'


def chips_html(p, n=3):
    t = "".join(f'<span class="fw-tag">{E(friendly(c))}</span>' for c in p["categories"][:n])
    if p["telehealth"]:
        t += f'<span class="fw-tag">{E(remote_label(p))}</span>'
    return t


def fee_from(p):
    m = re.search(r"\$\s?\d[\d,]*(?:\.\d\d)?", p.get("pricing") or "")
    return m.group(0).replace(" ", "") if m else ""


def since_txt(p):
    try:
        y = int(p.get("since"))
        return f"Since {y}" if 1900 < y <= YEAR else ""
    except (TypeError, ValueError):
        return ""


def wide_card(p):
    meta = " · ".join(x for x in [E(p["person"]) if p["person"] and p["person"] != p["name"] else "",
                                         f'{E(p["city"])}, {E(p["state"])}', since_txt(p)] if x)
    return f"""<a class="fw-card" href="/provider/{p['slug']}/">
        {avatar(p)}
        <span class="fw-card-body">
          <span class="fw-card-name">{E(p['name'])}</span>
          <span class="fw-card-meta">{meta}</span>
          <span class="fw-tags">{chips_html(p, 2)}{verify_tag(p)}</span>
        </span>
      </a>"""


def page_home():
    approved = [p for p in PROVIDERS if p["slug"] not in SEED_SLUGS]
    recent = [p for p in reversed(approved) if _has_logo(p)][:6]
    if len(recent) < 6:
        recent += [p for p in reversed(PROVIDERS) if p not in recent][:6 - len(recent)]
    faces = [p for p in PROVIDERS if _has_logo(p) and (p.get("logo") or "").startswith("/")
             and (p.get("verification") or {}).get("source")][:4]
    whereopts = "".join(f'<option value="{E(state_name(ab))}">' for ab in STATES)
    live = [d for d in DISCIPLINES if cat_count(d["key"])]
    tiles = [d for d in live if (d.get("img") or "").startswith("/assets/img/disciplines/")][:5]
    circles = "".join(
        f'<a class="fw-circle" href="/practice-types/{d["slug"]}/">'
        f'{img_tag(d["img"], "", "160px", widths=(500,))}<span>{E(friendly(d["key"]))}</span></a>'
        for d in tiles)
    more = len(DISCIPLINES) - len(tiles)
    faces_html = "".join(avatar(p) for p in faces)
    body = f"""  <section class="fw-hero">
    {LEAF_VEIN.replace('<svg ', '<svg class="fw-hero-leaf" ', 1)}
    <div class="wrap fw-hero-in">
      <div class="fw-hero-copy rise rise-1">
        <h1>Meet your practitioner <i>before</i> you book</h1>
        <p class="fw-hero-lede">Holistic and integrative care, with training, fees and licenses laid out plainly, so you can choose with confidence.</p>
        <form class="fw-search" id="console" action="/directory/" method="get">
          <label class="fw-search-f"><span>What kind of care?</span>
            <input id="c-q" name="q" type="search" placeholder="Ayurveda, acupuncture, nutrition"></label>
          <span class="fw-search-div" aria-hidden="true"></span>
          <label class="fw-search-f"><span>Where?</span>
            <input id="c-loc" name="where" type="text" placeholder="City, state or ZIP" list="where-list"></label>
          <datalist id="where-list">{whereopts}</datalist>
          <button class="fw-search-go" type="submit">Search</button>
        </form>
        <div class="fw-faces"><span class="fw-faces-row">{faces_html}</span>
          <span>{len(PROVIDERS)} practitioners in {len(STATES)} states, and growing
          &middot; <button type="button" class="fw-linkbtn" data-near="1" form="console">Use my location</button></span></div>
      </div>
      <div class="fw-hero-art rise rise-2">
        {HERO_FIGURE}
        {SPRIG.replace('<svg ', '<svg class="fw-hero-sprig" ', 1)}
      </div>
    </div>
  </section>

  <section class="wrap fw-sec fw-center">
    <h2>What kind of care are you looking for?</h2>
    <p class="fw-sub">{len(DISCIPLINES)} disciplines, each with its own page.</p>
    <div class="fw-circles">{circles}
      <a class="fw-circle" href="/practice-types/"><span class="fw-circle-more">and {more} more</span><span>See all</span></a>
    </div>
  </section>

  <section class="wrap fw-sec">
    <div class="fw-head"><h2>Recently joined</h2><a href="/directory/">See all practitioners</a></div>
    <div class="fw-cards">{"".join(wide_card(p) for p in recent)}</div>
  </section>

  <section class="fw-band">
    <div class="wrap fw-promises">
      <div>{SPRIG_SMALL}<h3>Checked where it counts</h3>
        <p>Licenses are confirmed with the state board that issued them, and the listing says when.</p></div>
      <div>{LEAF_PAIR}<h3>Honest about every tradition</h3>
        <p>Where a discipline has no license, we show training and certification instead, and say so plainly.</p></div>
      <div>{BUD}<h3>Nothing in between</h3>
        <p>You contact the practice directly. No commissions, no fees and no one paying for your details.</p></div>
    </div>
  </section>

  <section class="wrap fw-sec">
    <div class="fw-invite">
      {SPRIG.replace('<svg ', '<svg class="fw-invite-sprig" ', 1)}
      <div><h2>Are you a practitioner?</h2>
        <p>Listing is free and always will be. No paid placement, no leads sold. It takes about ten minutes.</p></div>
      <a class="btn btn-primary btn-lg" href="/join/">List your practice</a>
    </div>
  </section>"""
    return shell("FindWell Directory — holistic practitioners you can check",
                 "A free directory of holistic and integrative practitioners. Licensure, training, years in practice and pricing on every listing.",
                 "/", body, view="home",
                 extra_head=f'<link rel="preload" as="image" href="/assets/img/hero-1400.webp?v={IMG_V}" '
                            f'imagesrcset="/assets/img/hero-900.webp?v={IMG_V} 900w, /assets/img/hero-1400.webp?v={IMG_V} 1400w" '
                            f'imagesizes="(max-width:900px) 100vw, 470px" type="image/webp">')



def crumbs_html(trail):
    """trail is [(label, href or None), ...]; the last item is the current page."""
    parts = [f'<a href="{h}">{E(t)}</a>' if h else E(t) for t, h in trail]
    return '<p class="crumb">' + " / ".join(parts) + "</p>"

def page_directory(subset=None, title=None, desc=None, path="/directory/", heading=None,
                   intro="", trail=None, footer_link=None, current=None, art=None):
    rows = subset if subset is not None else PROVIDERS
    def _href(d):
        if not current:
            return ""
        return ' data-href="/directory/"' if d["key"] == current else f' data-href="/practice-types/{d["slug"]}/"'
    checks = "".join(
        f'<label class="check{"" if cat_count(d["key"]) else " check-empty"}">'
        f'<input type="checkbox" data-cat="{d["key"]}"{_href(d)}'
        f'{" checked" if d["key"] == current else ""}'
        f'{"" if cat_count(d["key"]) else " disabled"}> {E(friendly(d["key"]))}'
        f'<span class="n">{cat_count(d["key"])}</span></label>'
        for d in DISCIPLINES)
    stateopts = "".join(
        f'<option value="{ab}">{E(state_name(ab))} ({len(in_state(ab))})</option>'
        for ab in STATES)
    body = f"""{page_head(heading or 'Find care', E(intro) if intro else 'Every practitioner in the directory. Tell us where you are, then narrow it down by kind of care or telehealth.', trail or [("Home", "/"), (heading or "Find care", None)], art=art or (DISC_DRAWING.get(current) if current else "find"))}
  <div class="wrap dir">
      <aside class="rail" id="rail">
        <button class="rail-toggle" id="rail-toggle" aria-expanded="false">Narrow it down<span aria-hidden="true">&#9662;</span></button>
        <div class="rail-body">
          <p class="rail-title">Narrow it down</p>
          <div class="field">
            <label for="f-q">Name or keyword</label>
            <input class="control" id="f-q" type="search" placeholder="e.g. digestion, sciatica">
          </div>
          <fieldset><legend>Kind of care</legend>{checks}</fieldset>
          <fieldset><legend>State</legend>
            <select class="control" id="f-state"><option value="">All states</option>{stateopts}</select>
          </fieldset>
          <fieldset><legend>Show only</legend>
            <label class="check"><input type="checkbox" id="f-tele"> Offers telehealth or distance sessions</label>
          </fieldset>
          <button class="btn btn-ghost btn-sm" id="f-clear" type="button">Clear all filters</button>
        </div>
      </aside>
      <section class="dir-main">
        <form class="where-bar" id="where-bar" role="search">
          <label class="where-label" for="f-where">Where are you?</label>
          <div class="where-row">
            <input class="control where-input" id="f-where" type="text" placeholder="City, ZIP or postal code" autocomplete="off" enterkeyhint="search">
            <select class="control where-radius" id="f-radius" aria-label="Distance">
              <option value="10">Within 10 miles</option>
              <option value="25">Within 25 miles</option>
              <option value="50" selected>Within 50 miles</option>
              <option value="100">Within 100 miles</option>
              <option value="250">Within 250 miles</option>
              <option value="0">Any distance</option>
            </select>
            <button class="btn btn-dark where-go" type="submit">Search</button>
          </div>
          <p class="where-foot"><button type="button" class="fw-linkbtn" id="f-near">Use my location</button><span class="where-msg" id="geo-msg" aria-live="polite"></span></p>
        </form>
        <div class="results-bar">
          <p class="results-count" aria-live="polite"><b id="count">{len(rows)}</b> <span id="count-word">{'practitioner' if len(rows) == 1 else 'practitioners'}</span><span id="count-where"></span></p>
          <div class="sort">
            <label for="f-sort">Sort by</label>
            <select class="control" id="f-sort">
              <option value="name">Name</option>
              <option value="years">Years in practice</option>
              <option value="distance" disabled>Distance</option>
            </select>
          </div>
        </div>
        <div class="active-filters" id="active-filters"></div>
        <ul class="records" id="records">{"".join(record_html(p) for p in rows)}</ul>
        <p class="results-note">Every listing says how its credentials were established: checked with the issuing board, or as reported by the practitioner. <a href="/verification/">What that means</a></p>
        {f'<p class="back-link"><a href="{footer_link[1]}">&larr; {E(footer_link[0])}</a></p>' if footer_link else ''}
        <div class="empty" id="empty" hidden>
          <h3>No practitioners match those filters</h3>
          <p id="empty-msg">Try widening the distance, choosing another kind of care, or searching a nearby city. Many practitioners also offer telehealth.</p>
          <p id="empty-wider" hidden><button class="btn btn-ghost btn-sm" id="empty-widen" type="button"></button></p>
          <p><button class="btn btn-dark btn-sm" id="empty-clear" type="button">Clear filters</button></p>
        </div>
      </section>
  </div>"""
    return shell(title or "Find care — FindWell Directory",
                 desc or "Every practitioner in the FindWell Directory, filterable by discipline, city, distance and telehealth availability.",
                 path, body, view="directory")



def page_practice_types():
    cards = ""
    for d in DISCIPLINES:
        n = cat_count(d["key"])
        art = (img_tag(d["img"], "", "88px", widths=(500,)) if d.get("img")
               else f'<span class="fw-icon">{DISC_ICONS.get(d["key"], SPRIG_SMALL)}</span>')
        if n:
            cards += f"""<a class="fw-disc" href="/practice-types/{d['slug']}/">{art}<span>
          <span class="fw-disc-name">{E(friendly(d['key']))}</span>
          <span class="fw-disc-sub">{n} practitioner{'s' if n != 1 else ''} &middot; {E(DISC_BLURBS.get(d['key'], ''))}</span></span></a>"""
        else:
            cards += f"""<div class="fw-disc fw-disc-soon">{art}<span>
          <span class="fw-disc-name">{E(friendly(d['key']))}</span>
          <span class="fw-disc-sub">Coming soon</span></span></div>"""
    body = f"""{page_head("Every kind of care we list", f"{len(DISCIPLINES)} disciplines, from Ayurveda to your local farm. Choose one to see everyone who practises it.", [("Home", "/"), ("Disciplines", None)], art="bundle")}
  <section class="wrap fw-sec"><div class="fw-discs">{cards}</div>
    <p class="results-note">Licensure varies by discipline. Where a profession is licensed, we check the license with the state board. Where it is not, we show training and certification instead, and say so. <a href="/verification/">How we verify</a></p>
  </section>"""
    return shell("Disciplines — FindWell Directory",
                 "Browse holistic practitioners by discipline: Ayurveda, acupuncture, Chinese medicine, nutrition, integrative medicine, chiropractic, body work, energy work, herbal medicine and more.",
                 "/practice-types/", body)



def page_locations():
    cards = ""
    for ab in STATES:
        n = len(in_state(ab))
        cards += f"""<a class="fw-disc" href="/locations/{state_slug(ab)}/"><span class="fw-icon fw-icon-ab">{ab}</span><span>
          <span class="fw-disc-name">{E(state_name(ab))}</span>
          <span class="fw-disc-sub">{n} practitioner{'s' if n != 1 else ''} &middot; {E(', '.join(cities_in(ab))[:80])}</span></span></a>"""
    tele = sum(1 for p in PROVIDERS if p['telehealth'])
    body = f"""{page_head("Find care near you", f"Search from where you are, or browse by state. {tele} practitioners also offer telehealth, so distance needn't decide it.", [("Home", "/"), ("Locations", None)], art="desert")}
  <section class="wrap fw-sec">
    <form class="where-bar where-bar-lg" action="/directory/" method="get" role="search">
      <label class="where-label" for="loc-where">Where are you?</label>
      <div class="where-row">
        <input class="control where-input" id="loc-where" name="where" type="text" placeholder="City, ZIP or postal code" autocomplete="off" enterkeyhint="search" required>
        <button class="btn btn-dark where-go" type="submit">Find practitioners</button>
      </div>
      <p class="where-foot"><button type="button" class="fw-linkbtn" data-near-go="1">Use my location</button></p>
    </form>
    <h2 class="loc-h">Or browse by state</h2>
    <div class="fw-discs">{cards}</div>
  </section>"""
    return shell("Locations — FindWell Directory",
                 "Find holistic and integrative practitioners by state.", "/locations/", body)



def _social_label(u):
    host = u.split("//")[-1].replace("www.", "").split("/")[0].lower()
    known = {"facebook.com": "Facebook", "instagram.com": "Instagram", "linkedin.com": "LinkedIn",
             "youtube.com": "YouTube", "tiktok.com": "TikTok", "x.com": "X", "twitter.com": "X",
             "pinterest.com": "Pinterest", "threads.net": "Threads"}
    return known.get(host, host)

def page_provider(p):
    years = years_text(p, "years")
    maps = "https://www.google.com/maps/search/?api=1&query=" + (p["address"] or p["name"]).replace(" ", "+")
    nearby = [x for x in PROVIDERS if x["city"].lower() == p["city"].lower() and x["slug"] != p["slug"]]
    nearby.sort(key=lambda x: (not set(x["categories"]) & set(p["categories"]), not _has_logo(x)))
    nearby = nearby[:3]
    nearby_html = "".join(
        f'<a class="fw-mini" href="/provider/{x["slug"]}/">{avatar(x)}<span><span class="fw-mini-name">{E(x["name"])}</span>'
        f'<span class="fw-mini-sub">{E(", ".join(friendly(c) for c in x["categories"][:2]))}</span></span></a>'
        for x in nearby)
    social = "".join(
        f'<a href="{E(u)}" target="_blank" rel="noopener">{E(_social_label(u))}</a>'
        for u in p["social"] if u.startswith("http"))
    _disc = next((d for d in DISCIPLINES if d["key"] in p["categories"]), None)
    phone_digits = "".join(ch for ch in (p["phone"] or "") if ch.isdigit())
    site_label = (p["website"] or "").split("//")[-1].replace("www.", "").rstrip("/")
    fees = fee_items(p)
    ins = (p.get("insurance") or "").strip()
    lead_fee = fees[0] if fees and len(fees[0]) <= 40 else ("See fees below" if fees else "Ask the practice")
    facts = [("In practice", years.split(" (")[0] if years != "—" else "Not given"),
             ("Fees", lead_fee),
             ("Insurance", "Accepted" if ins.lower().startswith("accepted") else (ins or "Not given")),
             (("Telehealth", "Available" if p["telehealth"] else "In person only") if not p.get("remote_label")
              else ("Remote sessions", remote_label(p) + (" available" if p["telehealth"] else "")))]
    facts_html = "".join(f'<div class="fw-fact"><span class="k">{k}</span><span class="v">{E(v)}</span></div>'
                         for k, v in facts)
    v = p.get("verification")
    if v and v.get("source"):
        what = (v.get("what") or "").strip()
        detail = "" if re.match(r"(?i)^credentials? confirmed\b", what) else what
        verify_html = f"""<div class="fw-verify fw-verify-ok">{LEAF_ICON}
          <div><p class="fw-verify-t">Confirmed with {E(v['source'])}</p>
          <p class="fw-verify-d">{E(detail) + ", " if detail else ""}checked {E(v.get('date', ''))}. <a href="/verification/">What this means</a></p></div></div>"""
    else:
        verify_html = """<div class="fw-verify">
          <div><p class="fw-verify-t">As reported by the practitioner</p>
          <p class="fw-verify-d">We publish what the practitioner told us, and say so. <a href="/verification/">What this means</a></p></div></div>"""
    fee_rows = "".join(f'<div class="fw-fee">{E(x)}</div>' for x in fees) or \
        '<div class="fw-fee">Ask the practice about fees</div>'
    integ = ""
    if "IntegrativeMedicine" in p["categories"]:
        iv = (p.get("integrative_training") or "").strip()
        integ = f'<div class="fw-cred"><span class="k">Integrative training</span><span>{E(iv) if iv else "None reported"}</span></div>'
    ld = {"@context": "https://schema.org", "@type": "MedicalBusiness", "name": p["name"],
          "url": f"{SITE}/provider/{p['slug']}/", "telephone": p["phone"], "email": p["email"],
          "address": {"@type": "PostalAddress", "addressLocality": p["city"],
                      "addressRegion": p["state"], "postalCode": p["zip"]},
          "description": p["blurb"]}
    if p["address"]:
        ld["address"]["streetAddress"] = p["address"].split(",")[0]
    trail = [("Home", "/")] + ([(friendly(_disc["key"]), f"/practice-types/{_disc['slug']}/")] if _disc else []) + [(p["name"], None)]
    tags = "".join(f'<a class="fw-tag fw-tag-w" href="/practice-types/{disc(c)["slug"]}/">{E(friendly(c))}</a>' for c in p["categories"])
    body = f"""  <section class="pg-head fw-prof">
    {SPRIG.replace('<svg ', '<svg class="pg-leaf" ', 1)}
    <div class="wrap pg-head-in">
      {crumbs_html(trail)}
      <div class="fw-prof-head">
        {avatar(p, True)}
        <div class="fw-prof-id">
          <h1>{E(p['name'])}</h1>
          <p class="fw-prof-person">{E(p['person']) + ' &middot; ' if p['person'] and p['person'] != p['name'] else ''}{E(p['city'])}, {E(state_name(p['state']))}</p>
          <div class="fw-tags">{tags}</div>
        </div>
        <div class="fw-prof-actions">
          {f'<a class="btn btn-primary" href="tel:{phone_digits}">Call {E(p["phone"])}</a>' if phone_digits else ""}
          {f'<a class="btn btn-ghost" href="{E(p["website"])}" target="_blank" rel="noopener">Visit website</a>' if p["website"] else ""}
        </div>
      </div>
      <div class="fw-facts">{facts_html}</div>
    </div>
  </section>

  <div class="wrap fw-prof-body">
    <div class="fw-prof-main">
      {verify_html}
      <section><h2>About the practice</h2>
        <p class="fw-bio">{E(p['blurb'])}</p>
        {f'<p class="fw-bio fw-bio-soft">{E(p["long"])}</p>' if p['long'] else ''}
      </section>
      <section><h2>Fees</h2>
        <div class="fw-fees">{fee_rows}</div>
        <p class="fw-fee-foot">Payment: {val((p['payments'] or '').rstrip('. '))}. Insurance: {val((p['insurance'] or '').rstrip('. '))}.</p>
      </section>
      <section><h2>Training and credentials</h2>
        <div class="fw-creds">
          <div class="fw-cred"><span class="k">Credentials</span><span>{val(p['credentials'])}</span></div>
          <div class="fw-cred"><span class="k">Licensure</span><span>{val(p['licensure'])}</span></div>
          <div class="fw-cred"><span class="k">Training</span><span>{val(p['training'])}</span></div>
          {integ}
          <div class="fw-cred"><span class="k">In practice</span><span>{years}</span></div>
          <div class="fw-cred"><span class="k">Memberships</span><span>{val(p['affiliations'])}</span></div>
        </div>
      </section>
      {f'<section><h2>Also in {E(p["city"])}</h2><div class="fw-minis">{nearby_html}</div></section>' if nearby else ''}
    </div>
    <aside class="fw-prof-side">
      <div class="fw-contact">
        <p class="fw-contact-t">Get in touch</p>
        {f'<div class="fw-c"><span class="k">Phone</span><a href="tel:{phone_digits}">{E(p["phone"])}</a></div>' if phone_digits else ""}
        {f'<div class="fw-c"><span class="k">Email</span><a href="mailto:{E(p["email"])}">{E(p["email"])}</a></div>' if p["email"] else ""}
        {f'<div class="fw-c"><span class="k">Website</span><a href="{E(p["website"])}" target="_blank" rel="noopener">{E(site_label)}</a></div>' if p["website"] else ""}
        {f'<div class="fw-c"><span class="k">Address</span><span>{E(p["address"])}</span><a href="{maps}" target="_blank" rel="noopener">Open in Google Maps</a></div>' if p["address"] else '<div class="fw-c"><span class="k">Address</span><span>No public premises, visits by arrangement</span></div>'}
        {f'<div class="fw-social">{social}</div>' if social else ""}
        <p class="fw-contact-note">FindWell takes no commission and receives nothing when you book.</p>
      </div>
      <a class="fw-claim" href="mailto:{CONTACT_EMAIL}?subject={E(('Change to my listing: ' + p['name']).replace(' ', '%20'))}">Is this your practice? Ask us to update it</a>
    </aside>
  </div>"""
    head = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
    return shell(f"{p['name']} — {p['city']}, {p['state']} | FindWell Directory",
                 p["blurb"][:180], f"/provider/{p['slug']}/", body, extra_head=head)



# --- Application form vocabulary, matching the live Squarespace form ---
PAYMENT_METHODS = ["Insurance", "Cash", "Checks", "Credit Cards", "Debit Cards",
                   "HSA/FSA", "Paypal", "Venmo", "Zelle", "Crypto Wallet"]

SCOPE_OPTIONS = ["Ayurveda", "Acupuncture", "Traditional Chinese Medicine",
                 "Naturopathic Medicine", "Chiropractic", "Massage Therapy", "Body Work", "Energy Work",
                 "Integrative / Functional Medicine (MD, DO, NP, PA, RN)", "Counseling",
                 "Health & Wellness Coaching", "Nutrition (RD and Nutritionists)", "Herbalism", "Farmer", "Grocer"]

# FindWell lists practitioners in the United States and Canada only.
COUNTRIES = ["United States", "Canada"]

def yesno(name, label, hint="", req=True):
    return f"""<div class="field">
            <span class="lbl">{E(label)}{' *' if req else ''}</span>
            <div class="radio-row">
              <label class="check"><input type="radio" name="{name}" value="Yes"> Yes</label>
              <label class="check"><input type="radio" name="{name}" value="No"> No</label>
            </div>
            {f'<p class="hint">{E(hint)}</p>' if hint else ''}
            <p class="err" data-for="{name}">Choose one.</p>
          </div>"""

def page_join():
    scope = "".join(f'<button type="button" class="chip" data-jcat="{E(o)}" aria-pressed="false">{E(o)}</button>'
                    for o in SCOPE_OPTIONS)
    pay = "".join(f'<button type="button" class="chip" data-jpay="{E(o)}" aria-pressed="false">{E(o)}</button>'
                  for o in PAYMENT_METHODS)
    countries = "".join(
        '<option disabled>\u2014</option>' if c == "\u2014"
        else f'<option{" selected" if c == "United States" else ""}>{E(c)}</option>'
        for c in COUNTRIES)
    body = f"""{page_head("List your practice", "Listing is free and always will be. We publish exactly what you send, and where we check a credential with the issuing board, your listing says so and names the date. It takes about ten minutes.", [("Home", "/"), ("List your practice", None)], art="join")}
  <div class="wrap join-wrap">
    <div class="join-card">
      <div class="notice" id="join-gate" style="margin-top:2rem">
        <b>Listings are for individual practitioners.</b>
        Each listing carries one person's license, training and years in practice, which is what lets us tell a patient how those credentials were established. A practice as a whole cannot hold that, so practitioners who work together are listed side by side rather than as one entry. Practising under a business name is perfectly fine.
        <p style="margin:1.1rem 0 .5rem"><span class="lbl">Who is this application for? *</span></p>
        <div class="radio-row">
          <label class="check"><input type="radio" name="_applicant" value="self" checked> One practitioner, myself</label>
          <label class="check"><input type="radio" name="_applicant" value="group"> A group practice with several practitioners</label>
        </div>
      </div>

      <div class="notice" id="join-group" style="display:none;margin-top:1.6rem">
        <b>Wonderful, we would love to have your whole team.</b>
        Each practitioner applies separately, using the same practice name, so that every listing carries that person's own credentials. Below is a link you can send to your colleagues, which fills in your practice name for them.
        <div class="form-grid" style="margin-top:1.2rem">
          <div class="field full"><label for="j-gp-name">Practice name</label>
            <input class="control" id="j-gp-name" placeholder="Your practice or clinic name"></div>
          <div class="field full"><label for="j-gp-link">Link to share</label>
            <input class="control" id="j-gp-link" readonly value="{SITE}/join/"></div>
        </div>
        <p style="margin-top:1rem;display:flex;gap:.7rem;flex-wrap:wrap;align-items:center">
          <button type="button" class="btn btn-primary btn-sm" id="j-gp-copy">Copy the link</button>
          <a class="btn btn-dark btn-sm" id="j-gp-mail" href="#">Email it to your team</a>
          <span class="hint" id="j-gp-msg"></span>
        </p>
        <p class="hint" style="margin-top:1rem">If you also see patients yourself, choose "One practitioner, myself" above and apply as well.</p>
      </div>

      <form id="join-form" style="margin-top:2.6rem" novalidate
            action="{FORM_ENDPOINT}" method="POST" enctype="multipart/form-data">
        <input type="hidden" name="Scope of practice" id="j-cats-value">
        <input type="hidden" name="Payment methods" id="j-pay-value">
        <input type="hidden" name="_subject" id="j-subject" value="Directory application">
        <input type="hidden" name="Referred by" id="j-ref">
        <input type="text" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px">
        <div class="join-progress" id="join-progress" hidden>
          <p class="join-step-label" id="join-step-label">Step 1 of 5</p>
          <div class="join-bar" aria-hidden="true"><span id="join-bar-fill"></span></div>
        </div>

        <div class="join-step" data-step="1" data-name="About you">
        <section class="form-section">
          <h2>Let's start with you</h2>
          <div class="form-grid">
            <div class="field"><label for="j-first">First name *</label><input class="control" id="j-first" name="First name" autocomplete="given-name" required><p class="err">Required.</p></div>
            <div class="field"><label for="j-last">Last name *</label><input class="control" id="j-last" name="Last name" autocomplete="family-name" required><p class="err">Required.</p></div>
            <div class="field full"><label for="j-practice">Practice or business name *</label><input class="control" id="j-practice" name="Practice or business name" required><p class="err">Required.</p></div>
            <div class="field"><label for="j-email">Email *</label><input class="control" id="j-email" name="email" type="email" autocomplete="email" required><p class="err">Enter a working email address.</p></div>
            <div class="field"><label for="j-phone">Phone *</label><input class="control" id="j-phone" name="Phone" type="tel" autocomplete="tel" required><p class="err">Required.</p></div>
            <div class="field full"><label for="j-website">Website *</label><input class="control" id="j-website" name="Website" type="url" placeholder="http://" required><p class="err">Required.</p></div>
            <div class="field full"><label for="j-social">Social media</label><textarea class="control" id="j-social" name="Social media" placeholder="One URL per line."></textarea>
              <p class="hint">Add URLs for your Facebook, LinkedIn, Instagram or YouTube channels.</p></div>
          </div>
        </section>

        </div>
        <div class="join-step" data-step="2" data-name="Your practice">
        <section class="form-section">
          <h2>Where you practise</h2>
          <div class="form-grid">
            {yesno("physical", "Do you have a physical location?", "Answer No if you work from home or travel to clients.")}
            <div class="field"></div>
            <div class="field full" id="address-block">
              <span class="lbl">Address</span>
              <p class="hint" style="margin:-.15rem 0 .7rem">We will not publish this if you do not have a physical address where you provide services.</p>
            </div>
            <div class="field full"><label for="j-country">Country</label>
              <select class="control" id="j-country" name="Country">{countries}</select></div>
            <div class="field full"><label for="j-addr1">Address line 1</label><input class="control" id="j-addr1" name="Address line 1" autocomplete="address-line1"><p class="err">Required when you have a physical location.</p></div>
            <div class="field full"><label for="j-addr2">Address line 2</label><input class="control" id="j-addr2" name="Address line 2" autocomplete="address-line2"></div>
            <div class="field"><label for="j-city">City *</label><input class="control" id="j-city" name="City" autocomplete="address-level2" required><p class="err">Required.</p></div>
            <div class="field"><label for="j-state">State / Province *</label><input class="control" id="j-state" name="State" placeholder="AZ or ON" autocomplete="address-level1" required><p class="err">Required.</p></div>
            <div class="field"><label for="j-zip">ZIP / Postal code *</label><input class="control" id="j-zip" name="ZIP code" autocomplete="postal-code" required><p class="err">Required.</p></div>
          </div>
        </section>

        <section class="form-section">
          <h2>What you offer</h2>
          <div class="form-grid">
            <div class="field full"><span class="lbl">Which of the following best describes your services? *</span>
              <p class="hint" style="margin:-.15rem 0 .7rem">Select all that apply.</p>
              <p class="hint" style="margin:-.3rem 0 .7rem">Tick only what you are licensed or credentialed in. Other work you offer belongs in the description below.</p>
              <div class="chips" id="j-cats">{scope}</div>
              <p class="err" data-for="cats">Select at least one.</p></div>
            <div class="field full"><label for="j-short">Describe your practice *</label><textarea class="control" id="j-short" name="Describe your practice" required></textarea>
              <p class="hint">A brief description of your practice and services, 2\u20133 sentences. This is what appears on the directory and search pages.</p>
              <p class="err">Required.</p></div>
          </div>
        </section>

        <section class="form-section">
          <h2>Your listing page</h2>
          <div class="form-grid">
            <div class="field full"><label for="j-long">Give a description of your practice or business *</label>
              <textarea class="control" id="j-long" name="Listing description" style="min-height:170px" required></textarea>
              <p class="hint"><span id="wordcount">0</span> / 150 words. This appears on your own listing page.</p>
              <p class="err">Required.</p></div>
          </div>
        </section>
        </div>
        <div class="join-step" data-step="3" data-name="Your training">
        <section class="form-section">
          <h2>Your training and credentials</h2>
          <div class="notice verify-ask">
            <p><b>Would you like your listing to show as verified?</b> It gives patients more confidence when they are choosing a practitioner. Please include your state license number and any certifications or professional affiliations, and we will confirm them with the board or organisation that issued them.</p>
            <p>If you do not have any of these, you will still be listed, and your details will show as you reported them.</p>
          </div>
          <div class="form-grid">
            {yesno("licensed", "Do you hold a state license?", "Several disciplines here have no licensure route. Answering No is expected and is published as such.")}
            <div class="field"></div>
            <div class="field full"><label for="j-license">State license number(s)</label>
              <input class="control" id="j-license" name="State(s) and license number(s)" placeholder="Arizona, LAC-010717">
              <p class="hint">Include the state. Leave blank if your discipline has no state licensure.</p>
              <p class="licence-nudge" id="licence-nudge" hidden>You said you hold a state license. Adding the number lets us confirm it with the board, so your listing can show as verified.</p></div>
            <div class="field full"><label for="j-certs">Certifications and professional affiliations</label>
              <textarea class="control" id="j-certs" name="Certificates or affiliations" placeholder="NAMA Board Certified, Dipl. O.M. (NCCAOM), NBC-HWC, AHG Registered Herbalist, professional memberships&hellip;"></textarea>
              <p class="hint">Please fill this in whether or not you are licensed \u2014 board certifications and diplomate status belong here, and they appear on your listing.</p></div>
            <div class="field"><label for="j-since">How many years have you been in practice? *</label><input class="control" id="j-since" name="Years in practice" inputmode="numeric" placeholder="12" required><p class="err">Required.</p></div>
            <div class="field"></div>
            <div class="field full"><label for="j-training">Primary training and educational background *</label><textarea class="control" id="j-training" name="Primary training and education" placeholder="Programme, institution, hours completed." required></textarea><p class="err">Required.</p></div>
            <div class="field full"><label for="j-integrative">Integrative or functional medicine training</label>
              <textarea class="control" id="j-integrative" name="Integrative training" placeholder="e.g. IFM Certified Practitioner, ABOIM board certification, fellowship, coursework and hours."></textarea>
              <p class="hint">Publish exactly what you hold. If you have no formal integrative or functional training, leave this blank \u2014 the listing will say &ldquo;none reported&rdquo; rather than implying otherwise.</p></div>
          </div>
        </section>

        </div>
        <div class="join-step" data-step="4" data-name="Fees">
        <section class="form-section">
          <h2>Fees and payment</h2>
          <div class="form-grid">
            <div class="field full"><span class="lbl">Which of the following payments do you accept? *</span>
              <p class="hint" style="margin:-.15rem 0 .7rem">Select all that apply.</p>
              <div class="chips" id="j-pay">{pay}</div>
              <p class="err" data-for="pay">Select at least one.</p></div>
            <div class="field full"><label for="j-fees">Pricing structure *</label><textarea class="control" id="j-fees" name="Pricing structure" placeholder="Initial visit, follow-up, packages." required></textarea>
              <p class="hint">What do you charge for your services? List all that apply. A range is fine if pricing varies.</p>
              <p class="err">Required.</p></div>
            {yesno("telehealth", "Do you offer virtual/telehealth services?")}
          </div>
        </section>


        <section class="form-section internal">
          <h2>A few questions just for us</h2>
          <p class="hint" style="margin:-.4rem 0 1.2rem">These answers help us plan the directory. They never appear on your listing or anywhere public.</p>
          <div class="form-grid">
            <div class="field full"><label for="j-size">What is the desired size of your business or practice? *</label><textarea class="control" id="j-size" name="Desired size of practice" placeholder="Days per week, patient or customer numbers, or any other metric." required></textarea><p class="err">Required.</p></div>
            <div class="field full">
              <span class="lbl">Would you be open to accepting coverage for the care you provide? *</span>
              <p class="hint" style="margin:-.15rem 0 .7rem">Welliva Health, our partner project, is building coverage for integrative and lifestyle-based care, and is looking for practitioners to join that network. Listing here is free either way, and your answer has no bearing on whether your listing is published.</p>
              <div class="radio-row">
                <label class="check"><input type="radio" name="openins" value="Yes"> Yes</label>
                <label class="check"><input type="radio" name="openins" value="No"> No</label>
                <label class="check"><input type="radio" name="openins" value="Tell me more"> Tell me more</label>
              </div>
              <p class="err" data-for="openins">Choose one.</p>
            </div>
            {yesno("ehr", "Do you use an EHR? (Electronic Health Records)")}
          </div>
        </section>

        </div>
        <div class="join-step" data-step="5" data-name="Review and send">
        <section class="form-section">
          <h2>Your logo or photo</h2>
          <div class="form-grid">
            <div class="field full"><label for="j-files">Media</label>
              <input class="control file" id="j-files" name="Logo or headshot" type="file"
                     accept="image/*" multiple>
              <p class="hint">Upload your logo and/or headshot \u2014 maximum 2 images, 10 MB each. PNG or JPEG, square and 500px or larger works best.</p>
              <p class="err" data-for="files">Choose no more than two images, 10 MB each.</p>
              <p class="hint" id="file-list" style="margin-top:.4rem"></p></div>
          </div>
        </section>
        <section class="form-section">
          <h2>Confirm and send</h2>
          <label class="check attest" for="j-attest">
            <input type="checkbox" id="j-attest" name="Attestation" value="Agreed" required>
            <span>I confirm that the credentials, licenses, certifications and training I have
            given are accurate and current, that I am entitled to practise as described, and
            that I will notify FindWell Directory if any of it changes, lapses or is suspended.
            I understand my listing states how its credentials were established, and that
            unverified listings are published as reported by me.</span>
          </label>
          <p class="err" data-for="attest">This confirmation is required.</p>
          <div class="join-next-note"><b>What happens next</b> We will email you to say we have your application. Amita or Emma will review it, confirm your license or certification where we can, and email you again as soon as your listing is live.</div>
        </section>
        </div>

        <div class="join-nav">
          <button class="btn btn-ghost" type="button" id="j-back" hidden>Back</button>
          <span class="join-nav-gap"></span>
          <span class="hint" id="join-msg"></span>
          <button class="btn btn-primary" type="button" id="j-next" hidden>Continue</button>
          <button class="btn btn-primary" type="submit" id="j-send">Send my application</button>
        </div>
      </form>

      <div class="notice" id="join-done" style="display:none;margin-top:2rem">
        <b id="join-done-title">Thank you for your submission.</b>
        <span id="join-done-body"> We will get back to you shortly.</span>
        <p style="margin-top:.8rem" id="join-mail-wrap" hidden><a class="btn btn-dark btn-sm" id="join-mail" href="#">Open in email</a></p>
      </div>
    </div>
    <aside class="join-aside">
      {LEAF_VEIN.replace('<svg ', '<svg class="join-aside-leaf" ', 1)}
      <div class="fw-panel fw-panel-sage"><h3>Free, always</h3><p>No paid placement and no leads sold. Patients contact you directly.</p></div>
      <div class="fw-panel"><h3>Who can join</h3><p>Individual practitioners offering care in the United States or Canada. We do not list products.</p></div>
    </aside>
  </div>
  <script>(function(){{
    var q=new URLSearchParams(location.search);
    var el=function(id){{return document.getElementById(id);}};
    try{{
      var r=q.get("ref"); if(r)el("j-ref").value=r.slice(0,80);
      var pr=q.get("practice"); if(pr)el("j-practice").value=pr.slice(0,120);
    }}catch(e){{}}
    var form=el("join-form"), group=el("join-group"), name=el("j-gp-name"),
        link=el("j-gp-link"), mail=el("j-gp-mail"), msg=el("j-gp-msg");
    function shareUrl(){{
      var n=(name.value||"").trim();
      return "{SITE}/join/"+(n?"?practice="+encodeURIComponent(n):"");
    }}
    function refresh(){{
      link.value=shareUrl();
      mail.href="mailto:?subject="+encodeURIComponent("Join me on the FindWell Directory")
        +"&body="+encodeURIComponent("I am listing my practice on the FindWell Directory, a free "
        +"directory of holistic and integrative practitioners. Each practitioner applies "
        +"individually, so here is the link for you:\\n\\n"+shareUrl()
        +"\\n\\nIt takes about ten minutes and there is no cost.");
      msg.textContent="";
    }}
    Array.prototype.forEach.call(document.querySelectorAll('input[name="_applicant"]'),
      function(radio){{
        radio.addEventListener("change", function(){{
          var isGroup=radio.value==="group"&&radio.checked;
          group.style.display=isGroup?"":"none";
          form.style.display=isGroup?"none":"";
          if(isGroup){{refresh(); name.focus();}}
        }});
      }});
    name.addEventListener("input", refresh);
    el("j-gp-copy").addEventListener("click", function(){{
      link.select();
      var done=function(){{msg.textContent="Copied.";}};
      if(navigator.clipboard&&navigator.clipboard.writeText){{
        navigator.clipboard.writeText(link.value).then(done,function(){{document.execCommand("copy");done();}});
      }}else{{document.execCommand("copy");done();}}
    }});
    refresh();
  }})();</script>"""
    return shell("Join the directory \u2014 FindWell Directory",
                 "Practitioners: apply for a free listing in the FindWell Directory.",
                 "/join/", body, view="join")

WELLIVA_LOGO = "https://www.wellivahealth.com/welliva_logo_nav.png"

BANNER_PICTURE = f"""<picture>
      <source type="image/webp" sizes="100vw"
              srcset="/assets/img/banner-900.webp?v={BANNER_V} 900w, /assets/img/banner-1400.webp?v={BANNER_V} 1400w, /assets/img/banner-2000.webp?v={BANNER_V} 2000w">
      <img class="band-bg" src="/assets/img/banner-1400.jpg?v={BANNER_V}" sizes="100vw"
           srcset="/assets/img/banner-900.jpg?v={BANNER_V} 900w, /assets/img/banner-1400.jpg?v={BANNER_V} 1400w, /assets/img/banner-2000.jpg?v={BANNER_V} 2000w"
           width="2000" height="833" alt="" aria-hidden="true" loading="lazy" decoding="async">
    </picture>"""

ABOUT_BANNER = f"""<picture>
      <source type="image/webp" sizes="100vw"
              srcset="/assets/img/aboutbanner-900.webp?v={ABOUTB_V} 900w, /assets/img/aboutbanner-1400.webp?v={ABOUTB_V} 1400w, /assets/img/aboutbanner-2000.webp?v={ABOUTB_V} 2000w">
      <img class="page-banner-bg" src="/assets/img/aboutbanner-1400.jpg?v={ABOUTB_V}" sizes="100vw"
           srcset="/assets/img/aboutbanner-900.jpg?v={ABOUTB_V} 900w, /assets/img/aboutbanner-1400.jpg?v={ABOUTB_V} 1400w, /assets/img/aboutbanner-2000.jpg?v={ABOUTB_V} 2000w"
           width="2000" height="667" alt="" aria-hidden="true" fetchpriority="high">
    </picture>"""

ABOUT_PICTURE = f"""<picture>
          <source type="image/webp" sizes="(max-width:860px) 92vw, 70ch"
                  srcset="/assets/img/about-900.webp?v={ABOUT_V} 900w, /assets/img/about-1400.webp?v={ABOUT_V} 1400w, /assets/img/about-2000.webp?v={ABOUT_V} 2000w">
          <img src="/assets/img/about-1400.jpg?v={ABOUT_V}" sizes="(max-width:860px) 92vw, 70ch"
               srcset="/assets/img/about-900.jpg?v={ABOUT_V} 900w, /assets/img/about-1400.jpg?v={ABOUT_V} 1400w, /assets/img/about-2000.jpg?v={ABOUT_V} 2000w"
               width="2000" height="1000" alt="Hands cradling soil and a young seedling, overlaid with a network of connected points"
               loading="lazy" decoding="async">
        </picture>"""

def page_about():
    team = [("Amita Nathwani", "CEO"), ("Emma Vasseur", "Practitioner Liaison"), ("Sachin Bedi", "CTO")]
    team_html = "".join(f'<div class="fw-person"><span class="fw-mono">{E(initials(n))}</span>'
                        f'<span><span class="fw-person-name">{E(n)}</span><span class="fw-person-role">{E(r)}</span></span></div>'
                        for n, r in team)
    body = f"""{page_head("Who we are", "Prevention, transparency, and a direct line between practitioners and the people looking for them.", [("Home", "/"), ("About us", None)], art="hands")}
  <section class="wrap page-body">
    <p class="fw-big">FindWell Directory was born out of a simple but urgent mission: to change the conversation around healthcare in our country. Too often, access to healing is filtered through layers of insurance systems, hidden costs, and a pharmaceutical-driven model that doesn't reflect the diverse ways people actually seek wellness. We believe health should be rooted in prevention, transparency, and the empowerment of individuals to choose what works best for their bodies and their lives.</p>
    <p class="fw-big fw-soft">This project grew out of our work with Welliva Health, a new approach to healthcare financing that focuses on integrative and lifestyle-based care. While Welliva develops an alternative model of coverage, FindWell serves as its natural partner: a place where practitioners and patients connect directly, without middlemen. Practitioners openly share their credentials, services and pricing, and the people using the directory help us see the real needs in communities across the country.</p>
    <a class="fw-welliva" href="https://wellivahealth.com/" target="_blank" rel="noopener"><span>Health assurance for whole-person care</span><span>wellivahealth.com &rarr;</span></a>
  </section>
  <section class="wrap fw-sec fw-center">
    <h2>The people behind FindWell</h2>
    <div class="fw-team">{team_html}</div>
  </section>
  <section class="fw-band">
    <div class="wrap fw-three">
      <div class="fw-panel"><h3>What we verify</h3><p>For licensed professions we check the license number with the board that issued it and note the date. Where a discipline has no license, we record the training, the hours and any certification, and say plainly that no license exists. <a href="/verification/">More about this</a></p></div>
      <div class="fw-panel"><h3>What we don't do</h3><p>We don't evaluate clinical claims, host reviews, or vouch for outcomes. A listing means the credentials are as stated, nothing more. Complementary care works best alongside medical care, and we assume you have a physician too.</p></div>
      <div class="fw-panel"><h3>Get in touch</h3><p>Questions about a listing, a partnership, or the directory itself all come to one inbox: <a href="mailto:{CONTACT_EMAIL}?subject=FindWell%20enquiry">{CONTACT_EMAIL}</a>.</p></div>
    </div>
  </section>"""
    return shell("About us — FindWell Directory",
                 "FindWell Directory exists to change the conversation around healthcare: prevention, transparency, and direct connection between practitioners and patients. A partner project to Welliva Health.",
                 "/about/", body)



ARTICLES = [
    # Add posts here, newest first. `body` is raw HTML — paragraphs, h2s, lists.
    # dict(slug="choosing-an-acupuncturist", title="How to choose an acupuncturist",
    #      date="2026-09-01", author="Amita Nathwani",
    #      summary="What to ask before a first appointment, and what a licence does and doesn't tell you.",
    #      body="<p>…</p>"),
]

def article_card(a):
    return f"""<li><a class="index-row" href="/articles/{a['slug']}/">
      <span class="index-key">{E(a['date'][:7])}</span>
      <span class="index-name">{E(a['title'])}<span class="index-sub">{E(a.get('summary',''))}</span></span>
      <span class="index-n">Read</span></a></li>"""

def page_articles():
    if ARTICLES:
        inner = f'<ul class="index-list">{"".join(article_card(a) for a in ARTICLES)}</ul>'
    else:
        inner = """<div class="empty">
        <h3>Nothing published yet</h3>
        <p>We are writing about how to choose a practitioner, what a license does and does not tell you, and what integrative care costs. Check back soon.</p>
        <p><a class="btn btn-dark btn-sm" href="/directory/">Find a practitioner instead</a></p>
      </div>"""
    body = f"""{page_head("Articles", "Plain explanations of how holistic and integrative care works: what the credentials mean, what to ask, and what things cost.", [("Home", "/"), ("Articles", None)], art="book")}
  <section class="wrap page-body">
    {inner}
    <div class="fw-panel fw-panel-sage">
      <h3>Write for FindWell</h3>
      <p>Practitioners and researchers are welcome to propose a piece on credentials, costs, or how a discipline works in practice.</p>
      <p><a class="btn btn-dark btn-sm" href="mailto:{CONTACT_EMAIL}?subject=Article%20proposal">Propose an article</a></p>
    </div>
  </section>"""
    return shell("Articles — FindWell Directory",
                 "Plain explanations of how holistic and integrative care works: credentials, questions to ask, and what care costs.",
                 "/articles/", body)



def page_article(a):
    body = f"""{page_head(a['title'], E(a['date']) + (' &middot; ' + E(a['author']) if a.get('author') else ''), [("Home", "/"), ("Articles", "/articles/"), (a['title'], None)], art="book")}
  <article class="wrap page-body prose">{a['body']}
    <p><a class="btn btn-dark" href="/articles/">All articles</a></p>
  </article>"""
    return shell(f"{a['title']} — FindWell Directory",
                 a.get('summary', '')[:180], f"/articles/{a['slug']}/", body)



def page_advertise():
    body = f"""{page_head("Advertise with us", "FindWell reaches people at the moment they are choosing a practitioner: comparing credentials, weighing cost, deciding who to call. If you serve that audience, we would like to hear from you.", [("Home", "/"), ("Advertise with us", None)], art="branch")}
  <section class="wrap page-body">
    <div class="fw-panel fw-panel-honey">
      <h2>What we will never sell</h2>
      <p>Placement in the directory. Listings are free, ordered by relevance and distance, and no practitioner can pay to rank higher, appear first, or be marked as recommended. We do not sell leads or share the contact details of people using the site. That rule is the reason the directory is worth advertising in at all, and it is not for sale.</p>
    </div>
    <h2>What is available</h2>
    <div class="fw-three fw-three-tight">
      <div class="fw-panel"><h3>Sponsored articles</h3><p>Clearly labelled, editorially reviewed, and written to be useful rather than promotional.</p></div>
      <div class="fw-panel"><h3>Display placements</h3><p>On article pages and discipline pages, set apart from listings.</p></div>
      <div class="fw-panel"><h3>Partnerships</h3><p>Schools, professional associations, labs and insurers building something aligned with integrative care.</p></div>
    </div>
    <h2>Get in touch</h2>
    <p>Tell us who you are trying to reach and we will tell you honestly whether our audience is a fit. Rates depend on placement and season.</p>
    <p><a class="btn btn-primary" href="mailto:findwelldirectory@gmail.com?subject=Advertising%20enquiry">Email us about advertising</a></p>
  </section>"""
    return shell("Advertise with us — FindWell Directory",
                 "Reach people at the moment they are choosing a holistic practitioner. Sponsored articles, display placements and partnerships, never paid placement in the directory.",
                 "/advertise/", body)



def page_verification():
    body = f"""{page_head("How we verify", "Every listing says plainly how its credentials were established. There are two states, and you will see one of them on every listing.", [("Home", "/"), ("How we verify", None)], art="verify")}
  <section class="wrap page-body">
    <div class="fw-verify fw-verify-ok">{LEAF_ICON}<div>
      <p class="fw-verify-t">Confirmed with the Arizona Acupuncture Board of Examiners</p>
      <p class="fw-verify-d">License AC-4821, checked 25 Aug 2026.</p></div></div>
    <p>We checked directly with the body that issued the credential, and we name that body and the date we checked. A credential can lapse after a check, which is why the date is there.</p>
    <div class="fw-verify"><div>
      <p class="fw-verify-t">As reported by the practitioner</p>
      <p class="fw-verify-d">We publish what the practitioner told us, and say so.</p></div></div>
    <p>The practitioner told us their credentials and we published what they said. This is a normal, lasting state for a listing here, not a queue we are working through.</p>

    <h2>Three things people confuse</h2>
    <div class="fw-three fw-three-tight">
      <div class="fw-panel">{SPRIG_SMALL}<h3>A state license</h3><p>Issued by a government board that can revoke it. Acupuncturists, chiropractors, naturopathic doctors, counselors and massage therapists are licensed. Anyone can check a license number with the board, including you.</p></div>
      <div class="fw-panel">{LEAF_PAIR}<h3>A certification</h3><p>Comes from a private body with its own training and assessment, such as NAMA board certification in Ayurveda or NBC-HWC for health coaches. Real and meaningful, though no government stands behind it.</p></div>
      <div class="fw-panel">{BUD}<h3>A membership</h3><p>Something you join, usually by paying. It is not a credential, and we do not treat it as one, whatever it is called.</p></div>
    </div>

    <h2>Disciplines with no license at all</h2>
    <p>Ayurveda, herbalism, energy work and end-of-life support have no state licensure anywhere in the United States. That is not a gap in our checking, because there is no register to check. For those listings we publish the training, the hours and any certification, and we say that no license exists.</p>

    <h2>What practitioners agree to</h2>
    <p>Everyone who applies confirms that the credentials they give us are accurate and current, and agrees to tell us if anything changes, lapses or is suspended. If you believe a listing is inaccurate, <a href="mailto:{CONTACT_EMAIL}?subject=Listing%20query">tell us</a> and we will look into it.</p>

    <h2>What a listing is not</h2>
    <p>A listing is not a referral, a recommendation, or a judgement about anyone's competence. We publish credentials as stated and, where we have checked them, we say who with and when. Choosing a practitioner remains yours to do.</p>
    <p><a class="btn btn-dark" href="/directory/">Find a practitioner</a></p>
  </section>"""
    return shell("How we verify — FindWell Directory",
                 "How credentials on the FindWell Directory are established: what we check, what we don't, and the difference between a state license, a certification and a membership.",
                 "/verification/", body)



def page_404():
    body = f"""{page_head("That page isn't here", "The link may be out of date, or the listing may have been removed.", art="lost")}
  <section class="wrap page-body"><p><a class="btn btn-dark" href="/directory/">Find a practitioner</a> <a class="btn btn-ghost" href="/">Go to the home page</a></p></section>"""
    return shell("Page not found — FindWell Directory", "Page not found.", "/404", body)



# ---------------------------------------------------------------------------
def write(path, content):
    full = os.path.join(OUT, path.strip("/"))
    os.makedirs(os.path.dirname(full) if os.path.splitext(full)[1] else full, exist_ok=True)
    target = full if os.path.splitext(full)[1] else os.path.join(full, "index.html")
    with open(target, "w") as f:
        f.write(content)
    return target

def main():
    # Wipe generated pages first, so renamed or removed listings don't leave
    # orphaned URLs behind. Assets are left alone.
    for d in ("directory", "practice-types", "locations", "provider", "join",
              "about", "articles", "advertise", "verification"):
        shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)

    written = []
    written.append(write("index.html", page_home()))
    written.append(write("directory/", page_directory()))
    written.append(write("practice-types/", page_practice_types()))
    written.append(write("locations/", page_locations()))
    written.append(write("join/", page_join()))
    written.append(write("about/", page_about()))
    written.append(write("articles/", page_articles()))
    written.append(write("advertise/", page_advertise()))
    written.append(write("verification/", page_verification()))
    for a in ARTICLES:
        written.append(write(f"articles/{a['slug']}/", page_article(a)))
    written.append(write("404.html", page_404()))
    # what the Worker's review page needs to list every practitioner, including
    # the ones written into this file
    written.append(write("assets/data/providers.json", json.dumps([
        dict(slug=p["slug"], name=p["name"], person=p.get("person", ""),
             city=p["city"], state=p["state"], categories=p["categories"],
             licensure=p.get("licensure", ""), verification=p.get("verification"),
             seed=p["slug"] in SEED_SLUGS)
        for p in PROVIDERS], indent=1)))

    for d in DISCIPLINES:
        rows = [p for p in PROVIDERS if d["key"] in p["categories"]]
        written.append(write(f"practice-types/{d['slug']}/", page_directory(
            subset=rows,
            title=f"{d['label']} practitioners — FindWell Directory",
            desc=f"{d['label']}: {d['note']}",
            path=f"/practice-types/{d['slug']}/",
            heading=friendly(d["key"]), intro=d["note"].replace(" \u2014 ", ", ").replace(" — ", ", "),
            trail=[("Home", "/"), ("Disciplines", "/practice-types/"), (friendly(d["key"]), None)],
            footer_link=("All disciplines", "/practice-types/"), current=d["key"])))

    for ab in STATES:
        rows = in_state(ab)
        cs = cities_in(ab)
        written.append(write(f"locations/{state_slug(ab)}/", page_directory(
            subset=rows,
            title=f"Holistic practitioners in {state_name(ab)} — FindWell Directory",
            desc=f"{len(rows)} holistic and integrative practitioners listed in {state_name(ab)}.",
            path=f"/locations/{state_slug(ab)}/",
            heading=state_name(ab),
            intro=f"{len(rows)} listed in {state_name(ab)} — {', '.join(cs)}.",
            trail=[("Home", "/"), ("Locations", "/locations/"), (state_name(ab), None)],
            footer_link=("All locations", "/locations/"), art="desert")))

    for p in PROVIDERS:
        written.append(write(f"provider/{p['slug']}/", page_provider(p)))

    # sitemap + robots
    urls = ["/", "/directory/", "/practice-types/", "/locations/", "/join/", "/about/",
            "/articles/", "/advertise/", "/verification/"]
    urls += [f"/articles/{a['slug']}/" for a in ARTICLES]
    urls += [f"/practice-types/{d['slug']}/" for d in DISCIPLINES]
    urls += [f"/locations/{state_slug(ab)}/" for ab in STATES]
    urls += [f"/provider/{p['slug']}/" for p in PROVIDERS]
    today = datetime.date.today().isoformat()
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) +
          "</urlset>\n")
    write("sitemap.xml", sm)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")

    print(f"Built {len(written) + 2} files:")
    print(f"  {len(PROVIDERS)} provider pages")
    print(f"  {len(DISCIPLINES)} discipline pages")
    print(f"  {len(STATES)} state pages")
    print(f"  {len(ARTICLES)} article page(s)")
    print("  8 core pages, 404, sitemap.xml, robots.txt")

if __name__ == "__main__":
    main()
