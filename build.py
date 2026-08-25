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
import os, json, shutil, html, datetime, hashlib

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
         img=SS + "1755277939973-CMBB3T6JXU1IHOVFEOSH/unsplash-image-77vZsyvV0bg.jpg"),
    dict(key="Acupuncture", label="Acupuncture", slug="acupuncture",
         note="Licensed professionals — L.Ac.",
         img=SS + "1755277990849-EKKNDADU9C6IGG4FCL8D/unsplash-image-QgcdtM9rA5s.jpg"),
    dict(key="TCM", label="TCM", slug="traditional-chinese-medicine",
         note="Traditional Chinese Medicine — Dipl. O.M.",
         img=SS + "1755278047472-9EZGRJW7AO109Q8GK2D5/unsplash-image-ur2zmbseUIA.jpg"),
    dict(key="Naturopathy", label="Licensed naturopaths", slug="naturopathic-medicine",
         note="ND or NMD — licensed in Arizona.",
         img=SS + "1755278249101-I8FZPKRHUBB5G4P677O0/unsplash-image-KERVbxLVLiY.jpg"),
    dict(key="IntegrativeMedicine", label="Integrative & functional medicine",
         slug="integrative-functional-medicine",
         note="Licensed clinicians — MD, DO, NP or PA — practising integrative or functional medicine. Integrative training is published on every record, including when none is reported.",
         img="/assets/img/disciplines/integrative"),
    dict(key="Counseling", label="Counselors", slug="counseling",
         note="Licensed mental health professionals — LPC, LCSW, LMFT.",
         img=SS + "1757903674176-QK99BMSR1DQHPNWYLO3E/unsplash-image-F9DFuJoS9EU.jpg"),
    dict(key="Coaching", label="Health & wellness coaches", slug="health-wellness-coaching",
         note="Board certified coaches (NBC-HWC) and other non-clinical forms of support. No state licensure exists.",
         img="/assets/img/disciplines/coaching"),
    dict(key="Bodywork", label="Body work", slug="body-work",
         note="CranioSacral, tuina, structural integration. State licensed.",
         img=SS + "1755278329164-ATSTUR14YXFQDGE3ZFGI/unsplash-image-AV0KNliGvQc.jpg"),
    dict(key="EnergyMedicine", label="Energy healers", slug="energy-work",
         note="Reiki, Eden Energy Medicine, biofield therapies. Training shown; no licensure exists.",
         img=SS + "1755278519443-A0U3QGXU0WZX58E0VMA6/unsplash-image-QD7K3E9UTwI.jpg"),
    dict(key="Chiropractic", label="Chiropractors", slug="chiropractic",
         note="Doctor of Chiropractic — D.C., state licensed.",
         img=SS + "1755990861680-X13BU084AZ5IQFMMC1DT/unsplash-image-8qwYA4INVCk.jpg"),
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
         licensure="Arizona licensed acupuncturist — license no. pending verification",
         training="Emperor's College — Master of Traditional Oriental Medicine",
         since=2005, affiliations="—",
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
         pricing="New patient $450 · Follow-up $135",
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
        if not r.get("slug") or r["slug"] in have:
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
        PROVIDERS.append(r)
        have.add(r["slug"])
        added += 1
    if added:
        print(f"  + {added} listing(s) merged from data/listings.json")

_merge_approved()

E = html.escape

def disc(key):
    return next(d for d in DISCIPLINES if d["key"] == key)

def cat_count(key):
    return sum(1 for p in PROVIDERS if key in p["categories"])

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

def state_name(ab):
    return STATE_NAMES.get(ab, ab)

def state_slug(ab):
    return state_name(ab).lower().replace(" ", "-")

STATES = sorted({p["state"] for p in PROVIDERS}, key=state_name)
CITIES = sorted({(p["city"], p["state"]) for p in PROVIDERS})

def in_state(ab):
    return [p for p in PROVIDERS if p["state"] == ab]

def cities_in(ab):
    return sorted({p["city"] for p in in_state(ab)})

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

LOGO = IMG["logo"]          # still used for og:image until a share card exists

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

def shell(title, desc, path, body, view="", extra_head=""):
    """Wrap page content in the shared chrome. `path` is the canonical URL path."""
    # "Find a provider" opens a menu of the three ways in; the rest are plain links.
    find_links = [("/directory/", "All providers"),
                  ("/practice-types/", "By discipline"),
                  ("/locations/", "By location")]
    find_active = any(path.startswith(h) for h, _ in find_links)
    submenu = "".join(
        f'<li><a href="{h}"{" aria-current=\"page\"" if path.startswith(h) else ""}>{t}</a></li>'
        for h, t in find_links)

    nav = [("/about/", "Who we are"), ("/articles/", "Articles"),
           ("/advertise/", "Advertise with us")]
    navhtml = f"""<div class="nav-group">
        <button type="button" class="nav-toggle" id="find-toggle" aria-expanded="false"
                aria-controls="find-menu"{' data-active="1"' if find_active else ''}>
          Find a provider <span class="caret" aria-hidden="true">&#9662;</span>
        </button>
        <ul class="nav-menu" id="find-menu">{submenu}</ul>
      </div>""" + "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if path.startswith(h) else ""}>{t}</a>'
        for h, t in nav)

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
<meta property="og:image" content="{LOGO}?format=1500w">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css?v={CSS_V}">
{extra_head}
</head>
<body{f' data-view="{view}"' if view else ''}>
<a class="skip" href="#main">Skip to content</a>

<header class="masthead">
  <div class="wrap masthead-in">
    <a class="mark" href="/" aria-label="FindWell Directory — home">
      {LOGO_MARKUP}
    </a>
    <button class="burger" id="burger" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav class="nav" id="nav" aria-label="Main">
      {navhtml}
      <a class="cta" href="/join/">Join the directory</a>
    </nav>
  </div>
</header>

<main id="main">
{body}
</main>

<footer class="foot">
  <div class="wrap">
    <div class="foot-in">
      <div>
        <span class="foot-mark"><img src="/assets/img/logo-400.png?v={_v("assets/img/logo-400.png")}" width="965" height="289" alt="FindWell Directory" loading="lazy" decoding="async"></span>
        <p class="foot-blurb">A network of holistic and integrative practitioners. No commissions, no listing fees, no lead-selling.</p>
      </div>
      <div>
        <h4>Find care</h4>
        <a href="/directory/">Find a provider</a>
        <a href="/practice-types/">By discipline</a>
        <a href="/locations/">By location</a>
      </div>
      <div>
        <h4>More</h4>
        <a href="/join/">Join the directory</a>
        <a href="/about/">Who we are</a>
        <a href="/articles/">Articles</a>
        <a href="/advertise/">Advertise with us</a>
        <a href="/verification/">What verification means</a>
        <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
      </div>
    </div>
    <div class="foot-legal">
      <span>&copy; {YEAR} FindWell Directory.</span>
      <span>Listings are informational and are not a referral, endorsement, or medical advice.</span>
    </div>
  </div>
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

def tags_html(p):
    t = "".join(f'<a class="tag" href="/practice-types/{disc(c)["slug"]}/">{E(disc(c)["label"])}</a>'
                for c in p["categories"])
    if p["telehealth"]:
        t += '<span class="tag tag-tele">Telehealth</span>'
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
        return (f'<p class="verify verify-confirmed">'
                f'<b>{E(v.get("what", "Credential confirmed"))}</b> with {E(v["source"])}'
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

def record_html(p):
    years = f'{YEAR - p["since"]} yrs (since {p["since"]})'
    hay = " ".join([p["name"], p["person"], p["city"], p["state"], p["zip"],
                    p["credentials"], p["training"], p["blurb"], p["licensure"]] +
                   [disc(c)["label"] for c in p["categories"]]).lower()
    where = f'{E(p["city"])}, {E(p["state"])} {E(p["zip"])}'
    return f"""<li class="record" data-cats="{' '.join(p['categories'])}"
      data-city="{E(p['city'])}" data-state="{p['state']}" data-tele="{1 if p['telehealth'] else 0}"
      data-lat="{p['lat']}" data-lng="{p['lng']}" data-since="{p['since']}"
      data-name="{E(p['name'])}" data-text="{E(hay)}">
    <article class="record-in">
      <div class="record-head">
        {avatar(p)}
        <div>
          <h3 class="record-name"><a href="/provider/{p['slug']}/">{E(p['name'])}</a></h3>
          <p class="record-person"><b>{E(p['person'])}</b></p>
          <p class="record-where">{where} <span class="record-dist"></span></p>
          {tags_html(p)}
        </div>
      </div>
      <dl class="fields">
        <dt>Credential</dt><dd>{E(p['credentials'])}</dd>
        <dt>Licensure</dt><dd>{E(p['licensure'])}</dd>
        {integrative_row(p)}
        <dt>In practice</dt><dd>{years}</dd>
        <dt>Fees</dt><dd>{E(p['pricing'])}</dd>
        <dt>Insurance</dt><dd>{E(p['insurance'])}</dd>
      </dl>
      <div class="record-verify">{verification_line(p)}</div>
      <div class="record-actions">
        <a class="btn btn-ghost btn-sm" href="/provider/{p['slug']}/">Full record</a>
        {f'<a class="btn btn-ghost btn-sm" href="tel:{"".join(ch for ch in p["phone"] if ch.isdigit())}">{E(p["phone"])}</a>' if p["phone"] else ""}
        <a class="btn btn-ghost btn-sm" href="mailto:{E(p['email'])}">Email</a>
      </div>
    </article>
  </li>"""

# ---------------------------------------------------------------------------
def page_home():
    ndisc = sum(1 for d in DISCIPLINES if cat_count(d["key"]))
    body = f"""  <section class="hero">
    {HERO}
    <div class="wrap hero-in">
      <div class="hero-panel rise rise-1">
        <h1>Find trusted holistic practitioners <em>whose credentials you can read</em> before you call.</h1>
        <p class="hero-lede">Every listing shows licensure, where they trained, how long they have practised, what a visit costs, and whether they bill insurance. No commissions, no paid placement, no lead selling.</p>
        <p class="hero-stats">
          <span><b>{len(PROVIDERS)}</b> practitioners</span>
          <span><b>{ndisc}</b> disciplines</span>
          <span><b>{len(STATES)}</b> states</span>
          <span><b>{sum(1 for p in PROVIDERS if p['telehealth'])}</b> offer telehealth</span>
        </p>
      </div>
    </div>
  </section>

  <section class="console-strip">
    <div class="wrap rise rise-2">{console_html()}</div>
  </section>

  <section class="section">
    <div class="wrap">
      <h2>How it works</h2>
      <div class="steps">
        <div class="step"><h3>Search by discipline or distance</h3><p>Filter by practice type, city, ZIP radius, or telehealth availability. Combine as many filters as you need.</p></div>
        <div class="step"><h3>Read the record</h3><p>State license number where one exists, training institution, years in practice, fee schedule and insurance status — in the same place on every listing. Each one also says how its credentials were established. <a href="/verification/">What that means</a>.</p></div>
        <div class="step"><h3>Contact them directly</h3><p>Phone, email and website go straight to the practice. Nothing routes through us and no one pays for your contact details.</p></div>
      </div>
    </div>
  </section>

  <section class="band-feature">
    {BANNER_PICTURE}
    <div class="wrap band-feature-in">
      <h2>About the directory</h2>
      <p>There is no centralised system for non-insurance-based care, which makes a first appointment a guess. We collect the same facts from every practitioner and publish them in the same shape, so the comparison is yours to make.</p>
      <ul>
        <li>Every listing carries state licensure where it applies, years in practice, pricing structure, insurance status and direct contact details.</li>
        <li>For disciplines with no licensure route \u2014 Ayurveda, herbalism, energy medicine \u2014 we publish training and voluntary certification instead, and say plainly that no license exists.</li>
        <li>No middlemen, no commissions, no listing fees. Nothing routes through us and no one pays for placement.</li>
      </ul>
      <p style="margin-top:1.8rem"><a class="btn btn-primary" href="/directory/">Find a provider</a></p>
    </div>
  </section>"""
    return shell("FindWell Directory — trusted holistic practitioners",
                 "A searchable directory of vetted holistic and integrative practitioners. Filter by discipline, city or distance. Licensure, training, years in practice and pricing on every record.",
                 "/", body, view="home",
                 extra_head=f'<link rel="preload" as="image" href="/assets/img/hero-1400.webp?v={IMG_V}" '
                            f'imagesrcset="/assets/img/hero-900.webp?v={IMG_V} 900w, /assets/img/hero-1400.webp?v={IMG_V} 1400w, '
                            f'/assets/img/hero-2000.webp?v={IMG_V} 2000w" imagesizes="100vw" type="image/webp">')

def crumbs_html(trail):
    """trail is [(label, href or None), ...]; the last item is the current page."""
    parts = [f'<a href="{h}">{E(t)}</a>' if h else E(t) for t, h in trail]
    return '<p class="crumb">' + " / ".join(parts) + "</p>"

def page_directory(subset=None, title=None, desc=None, path="/directory/", heading=None,
                   intro="", trail=None, footer_link=None):
    rows = subset if subset is not None else PROVIDERS
    checks = "".join(
        f'<label class="check"><input type="checkbox" data-cat="{d["key"]}"> {E(d["label"])}'
        f'<span class="n">{cat_count(d["key"])}</span></label>'
        for d in DISCIPLINES if cat_count(d["key"]))
    stateopts = "".join(
        f'<option value="{ab}">{E(state_name(ab))} ({len(in_state(ab))})</option>'
        for ab in STATES)
    body = f"""  <div class="wrap">
    {crumbs_html(trail or [("Home", "/"), (heading or "Directory", None)])}
    <h1 style="font-size:clamp(1.9rem,4vw,2.6rem);margin:.6rem 0 1.4rem">{E(heading or 'Provider directory')}</h1>
    {f'<p class="lede" style="margin:-.8rem 0 1.8rem">{E(intro)}</p>' if intro else ''}
    <div class="dir">
      <aside class="rail" id="rail">
        <button class="rail-toggle" id="rail-toggle" aria-expanded="false">Filters<span>▾</span></button>
        <div class="rail-body">
          <div class="field" style="margin-bottom:1.6rem">
            <label for="f-q">Keyword</label>
            <input class="control" id="f-q" type="search" placeholder="Name, condition, credential">
          </div>
          <fieldset><legend>Discipline</legend>{checks}</fieldset>
          <fieldset><legend>State</legend>
            <select class="control" id="f-state"><option value="">All states</option>{stateopts}</select>
          </fieldset>
          <fieldset><legend>Distance</legend>
            <input class="control" id="f-zip" type="text" inputmode="numeric" placeholder="ZIP code">
            <label class="lbl" for="f-radius" style="margin-top:.7rem">Within 50 miles</label>
            <input id="f-radius" type="range" min="5" max="500" step="5" value="50" style="width:100%;accent-color:var(--brand)">
            <button class="btn btn-ghost btn-sm" id="f-near" style="width:100%;margin-top:.6rem">Use my location</button>
            <p class="hint" id="geo-msg"></p>
          </fieldset>
          <fieldset><legend>Format</legend>
            <label class="check"><input type="checkbox" id="f-tele"> Offers telehealth</label>
          </fieldset>
          <button class="btn btn-ghost btn-sm" id="f-clear" style="width:100%">Clear all filters</button>
        </div>
      </aside>
      <section>
        <div class="results-bar">
          <p class="results-count" aria-live="polite"><b id="count">{len(rows)}</b> <span id="count-word">{'practitioner' if len(rows) == 1 else 'practitioners'}</span><span id="count-where"></span></p>
          <div class="sort">
            <label for="f-sort">Sort</label>
            <select class="control" id="f-sort">
              <option value="name">Name</option>
              <option value="years">Years in practice</option>
              <option value="distance" disabled>Distance</option>
            </select>
          </div>
        </div>
        <p class="results-note">Every listing states how its credentials were established — checked with the issuing board, or as reported by the practitioner. <a href="/verification/">What that means</a>.</p>
        <div class="active-filters" id="active-filters"></div>
        <ul class="records" id="records">{"".join(record_html(p) for p in rows)}</ul>
        {f'<p class="back-link"><a href="{footer_link[1]}">&larr; {E(footer_link[0])}</a></p>' if footer_link else ''}
        <div class="empty" id="empty" hidden style="margin-top:2rem">
          <h3>No practitioners match those filters</h3>
          <p>Try widening the distance, removing a discipline, or searching a nearby city. Telehealth listings serve patients anywhere in their state.</p>
          <p style="margin-top:1.2rem"><button class="btn btn-dark btn-sm" id="empty-clear">Clear filters</button></p>
        </div>
      </section>
    </div>
  </div>
  <div style="height:4rem"></div>"""
    return shell(title or "Provider directory — FindWell Directory",
                 desc or "Every practitioner in the FindWell Directory, filterable by discipline, city, distance and telehealth availability.",
                 path, body, view="directory")

def page_practice_types():
    tiles = ""
    for d in DISCIPLINES:
        n = cat_count(d["key"])
        frame = (f'<div class="tile-frame">{img_tag(d["img"], "", "(max-width:700px) 92vw, 320px", widths=(500, 750, 1000))}</div>'
                 if d["img"] else f'<div class="tile-frame blank">{E(d["label"])}</div>')
        go = (f'<span class="tile-go">View providers <span class="n">{n}</span> \u2192</span>'
              if n else '<span class="tile-go none">No listings yet</span>')
        tiles += f"""<li><a class="tile" href="/practice-types/{d['slug']}/">
        {frame}<h3>{E(d['label'])}</h3><p>{E(d['note'])}</p>{go}</a></li>"""
    body = f"""  <div class="wrap">
    {crumbs_html([("Home", "/"), ("Find a provider", "/directory/"), ("By discipline", None)])}
    <div class="section-tight">
      <h1 style="font-size:clamp(1.9rem,4vw,2.6rem);margin-bottom:.8rem">Choose the type of practice</h1>
      <p class="lede">Licensure varies by discipline. Where a profession is state licensed, the license number appears on the record. Where it is not, we publish training and certification instead — and say so plainly. <a href="/verification/">What verification means here</a>.</p>
      <ul class="tiles">{tiles}</ul>
    </div>
  </div>
  <div style="height:3rem"></div>"""
    return shell("Browse by discipline \u2014 FindWell Directory",
                 "Browse holistic practitioners by discipline: Ayurveda, acupuncture, TCM, integrative and functional medicine, chiropractic, body work, energy work, herbology and more.",
                 "/practice-types/", body)

def page_locations():
    rows = ""
    for ab in STATES:
        n = len(in_state(ab))
        rows += f"""<li><a class="index-row" href="/locations/{state_slug(ab)}/">
        <span class="index-key">{ab}</span>
        <span class="index-name">{E(state_name(ab))}<span class="index-sub">{E(' · '.join(cities_in(ab)))}</span></span>
        <span class="index-n">{n}</span></a></li>"""
    body = f"""  <div class="wrap">
    {crumbs_html([("Home", "/"), ("Find a provider", "/directory/"), ("By location", None)])}
    <div class="section-tight">
      <h1 style="font-size:clamp(1.9rem,4vw,2.6rem);margin-bottom:.8rem">Browse by state</h1>
      <p class="lede">Pick a state, then narrow by city or ZIP radius once you are there. {sum(1 for p in PROVIDERS if p['telehealth'])} listings also offer telehealth, which in most disciplines means anywhere in the state they are licensed.</p>
      <ul class="index-list">{rows}</ul>
    </div>
  </div>
  <div style="height:3rem"></div>"""
    return shell("Browse by state — FindWell Directory",
                 "Find holistic and integrative practitioners by state.",
                 "/locations/", body)

def page_provider(p):
    years = f'{YEAR - p["since"]} years (since {p["since"]})'
    maps = "https://www.google.com/maps/search/?api=1&query=" + (p["address"] or p["name"]).replace(" ", "+")
    nearby = [x for x in PROVIDERS if x["city"] == p["city"] and x["slug"] != p["slug"]][:4]
    nearby_html = "".join(
        f'<div class="contact-row"><span class="k">{E(disc(x["categories"][0])["label"].split()[0])}</span>'
        f'<a href="/provider/{x["slug"]}/">{E(x["name"])}</a></div>' for x in nearby) or \
        '<p class="hint">No other listings in this city yet.</p>'
    social = "".join(
        f'<div class="contact-row"><span class="k">Social</span><a href="{E(u)}" target="_blank" rel="noopener">'
        f'{E(u.split("//")[-1].replace("www.", "").rstrip("/"))}</a></div>'
        for u in p["social"] if u.startswith("http"))
    ld = {"@context": "https://schema.org", "@type": "MedicalBusiness", "name": p["name"],
          "url": f"{SITE}/provider/{p['slug']}/", "telephone": p["phone"], "email": p["email"],
          "address": {"@type": "PostalAddress", "addressLocality": p["city"],
                      "addressRegion": p["state"], "postalCode": p["zip"]},
          "description": p["blurb"]}
    if p["address"]:
        ld["address"]["streetAddress"] = p["address"].split(",")[0]
    body = f"""  <div class="wrap">
    <p class="crumb"><a href="/">Home</a> / <a href="/directory/">Directory</a> / {E(p['name'])}</p>
    <div class="detail">
      <div>
        {avatar(p, True)}
        <h1>{E(p['name'])}</h1>
        <p class="detail-person">{E(p['person'])}</p>
        {tags_html(p)}
        {verification_line(p)}
        <p class="detail-bio" style="margin-top:1.6rem">{E(p['blurb'])}</p>
        {f'<p class="detail-bio">{E(p["long"])}</p>' if p['long'] else ''}
        <div class="detail-fields">
          <h3 style="font-family:var(--ff-display);font-size:1.15rem;margin-bottom:1rem;padding-bottom:.6rem;border-bottom:1px solid var(--line)">Practice record</h3>
          <dl class="fields">
            <dt>Credentials</dt><dd>{E(p['credentials'])}</dd>
            <dt>Licensure</dt><dd>{E(p['licensure'])}</dd>
            <dt>Training</dt><dd>{E(p['training'])}</dd>
            {integrative_row(p)}
            <dt>In practice</dt><dd>{years}</dd>
            <dt>Affiliations</dt><dd>{E(p['affiliations'])}</dd>
            <dt>Fees</dt><dd>{E(p['pricing'])}</dd>
            <dt>Payment</dt><dd>{E(p['payments'])}</dd>
            <dt>Insurance</dt><dd>{E(p['insurance'])}</dd>
            <dt>Telehealth</dt><dd>{'Yes' if p['telehealth'] else 'In person only'}</dd>
          </dl>
        </div>
      </div>
      <div>
        <div class="panel">
          <h3>Contact the practice</h3>
          {f'<div class="contact-row"><span class="k">Phone</span><a href="tel:{"".join(ch for ch in p["phone"] if ch.isdigit())}">{E(p["phone"])}</a></div>' if p["phone"] else ""}
          <div class="contact-row"><span class="k">Email</span><a href="mailto:{E(p['email'])}">{E(p['email'])}</a></div>
          <div class="contact-row"><span class="k">Web</span><a href="{E(p['website'])}" target="_blank" rel="noopener">{E(p['website'].split('//')[-1].replace('www.', '').rstrip('/'))}</a></div>
          {f'<div class="contact-row"><span class="k">Address</span><a href="{maps}" target="_blank" rel="noopener">{E(p["address"])}</a></div>' if p["address"] else '<div class="contact-row"><span class="k">Address</span><span>No public premises — visits by arrangement</span></div>'}
          {social}
          <p class="hint" style="margin-top:1rem">FindWell takes no commission and receives nothing when you book.</p>
        </div>
        <div class="panel">
          <h3>Nearby in {E(p['city'])}</h3>
          {nearby_html}
        </div>
      </div>
    </div>
  </div>"""
    head = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
    return shell(f"{p['name']} — {p['city']}, {p['state']} | FindWell Directory",
                 p["blurb"][:180], f"/provider/{p['slug']}/", body, extra_head=head)

# --- Application form vocabulary, matching the live Squarespace form ---
PAYMENT_METHODS = ["Insurance", "Cash", "Checks", "Credit Cards", "Debit Cards",
                   "HSA/FSA", "Paypal", "Venmo", "Zelle", "Crypto Wallet"]

SCOPE_OPTIONS = ["Ayurveda", "Acupuncture", "Traditional Chinese Medicine",
                 "Naturopathic Medicine", "Chiropractic", "Body Work", "Energy Work",
                 "Integrative / Functional Medicine", "Counseling",
                 "Health & Wellness Coaching", "Herbalism", "Farmer", "Grocer"]

COUNTRIES = ["United States", "Canada", "Mexico", "United Kingdom", "Australia", "\u2014",
    "Afghanistan","\u00c5land Islands","Albania","Algeria","American Samoa","Andorra","Angola",
    "Anguilla","Antigua & Barbuda","Argentina","Armenia","Aruba","Ascension Island","Austria",
    "Azerbaijan","Bahamas","Bahrain","Bangladesh","Barbados","Belarus","Belgium","Belize","Benin",
    "Bermuda","Bhutan","Bolivia","Bosnia & Herzegovina","Botswana","Brazil",
    "British Indian Ocean Territory","British Virgin Islands","Brunei","Bulgaria","Burkina Faso",
    "Burundi","Cambodia","Cameroon","Cape Verde","Caribbean Netherlands","Cayman Islands",
    "Central African Republic","Chad","Chile","China","Christmas Island","Cocos (Keeling) Islands",
    "Colombia","Comoros","Congo - Brazzaville","Congo - Kinshasa","Cook Islands","Costa Rica",
    "C\u00f4te d\u2019Ivoire","Croatia","Cuba","Cura\u00e7ao","Cyprus","Czechia","Denmark","Djibouti",
    "Dominica","Dominican Republic","Ecuador","Egypt","El Salvador","Equatorial Guinea","Eritrea",
    "Estonia","Eswatini","Ethiopia","Falkland Islands","Faroe Islands","Fiji","Finland","France",
    "French Guiana","French Polynesia","Gabon","Gambia","Georgia","Germany","Ghana","Gibraltar",
    "Greece","Greenland","Grenada","Guadeloupe","Guam","Guatemala","Guernsey","Guinea",
    "Guinea-Bissau","Guyana","Haiti","Honduras","Hong Kong SAR China","Hungary","Iceland","India",
    "Indonesia","Iran","Iraq","Ireland","Isle of Man","Israel","Italy","Jamaica","Japan","Jersey",
    "Jordan","Kazakhstan","Kenya","Kiribati","Kosovo","Kuwait","Kyrgyzstan","Laos","Latvia",
    "Lebanon","Lesotho","Liberia","Libya","Liechtenstein","Lithuania","Luxembourg",
    "Macao SAR China","Madagascar","Malawi","Malaysia","Maldives","Mali","Malta","Marshall Islands",
    "Martinique","Mauritania","Mauritius","Mayotte","Micronesia","Moldova","Monaco","Mongolia",
    "Montenegro","Montserrat","Morocco","Mozambique","Myanmar (Burma)","Namibia","Nauru","Nepal",
    "Netherlands","New Caledonia","New Zealand","Nicaragua","Niger","Nigeria","Niue",
    "Norfolk Island","Northern Mariana Islands","North Korea","North Macedonia","Norway","Oman",
    "Pakistan","Palau","Palestinian Territories","Panama","Papua New Guinea","Paraguay","Peru",
    "Philippines","Poland","Portugal","Puerto Rico","Qatar","R\u00e9union","Romania","Russia","Rwanda",
    "Samoa","San Marino","S\u00e3o Tom\u00e9 & Pr\u00edncipe","Saudi Arabia","Senegal","Serbia","Seychelles",
    "Sierra Leone","Singapore","Sint Maarten","Slovakia","Slovenia","Solomon Islands","Somalia",
    "South Africa","South Korea","South Sudan","Spain","Sri Lanka","St. Barth\u00e9lemy","St. Helena",
    "St. Kitts & Nevis","St. Lucia","St. Martin","St. Pierre & Miquelon","St. Vincent & Grenadines",
    "Sudan","Suriname","Svalbard & Jan Mayen","Sweden","Switzerland","Syria","Taiwan","Tajikistan",
    "Tanzania","Thailand","Timor-Leste","Togo","Tokelau","Tonga","Trinidad & Tobago",
    "Tristan da Cunha","Tunisia","T\u00fcrkiye","Turkmenistan","Turks & Caicos Islands","Tuvalu",
    "U.S. Virgin Islands","Uganda","Ukraine","United Arab Emirates","Uruguay","Uzbekistan","Vanuatu",
    "Vatican City","Venezuela","Vietnam","Wallis & Futuna","Western Sahara","Yemen","Zambia",
    "Zimbabwe"]

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
    body = f"""  <div class="wrap">
    <p class="crumb"><a href="/">Home</a> / Join</p>
    <div class="section-tight" style="max-width:860px">
      <h1 style="font-size:clamp(1.9rem,4vw,2.6rem);margin-bottom:.8rem">Join the directory</h1>
      <p class="lede">Listings are free. We publish exactly what you send \u2014 including the absence of a license where none exists for your discipline. Where we have checked a credential with the issuing board, your listing says so and names the date; where we have not, it says the details are as you reported them. <a href="/verification/">What verification means here</a>. Fields marked * are required.</p>

      <form id="join-form" style="margin-top:2.6rem" novalidate
            action="{FORM_ENDPOINT}" method="POST" enctype="multipart/form-data">
        <input type="hidden" name="Scope of practice" id="j-cats-value">
        <input type="hidden" name="Payment methods" id="j-pay-value">
        <input type="hidden" name="_subject" id="j-subject" value="Directory application">
        <input type="text" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px">

        <section class="form-section">
          <h2>Provider name</h2>
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

        <section class="form-section">
          <h2>Location</h2>
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
            <div class="field"><label for="j-state">State *</label><input class="control" id="j-state" name="State" placeholder="AZ" autocomplete="address-level1" required><p class="err">Required.</p></div>
            <div class="field"><label for="j-zip">ZIP code *</label><input class="control" id="j-zip" name="ZIP code" inputmode="numeric" autocomplete="postal-code" required><p class="err">Required.</p></div>
          </div>
        </section>

        <section class="form-section">
          <h2>Scope of practice</h2>
          <div class="form-grid">
            <div class="field full"><span class="lbl">Which of the following best describes your services? *</span>
              <p class="hint" style="margin:-.15rem 0 .7rem">Select all that apply.</p>
              <div class="chips" id="j-cats">{scope}</div>
              <p class="err" data-for="cats">Select at least one.</p></div>
            <div class="field full"><label for="j-short">Describe your practice *</label><textarea class="control" id="j-short" name="Describe your practice" required></textarea>
              <p class="hint">A brief description of your practice and services, 2\u20133 sentences. This is what appears on the directory and search pages.</p>
              <p class="err">Required.</p></div>
          </div>
        </section>

        <section class="form-section">
          <h2>Credentials &amp; experience</h2>
          <div class="form-grid">
            {yesno("licensed", "Do you hold a state license?", "Several disciplines here have no licensure route. Answering No is expected and is published as such.")}
            <div class="field"></div>
            <div class="field full"><label for="j-license">If yes, list state(s) and license number(s)</label><input class="control" id="j-license" name="State(s) and license number(s)" placeholder="Arizona, LAC-010717"></div>
            <div class="field full"><label for="j-certs">If no, list your certificates or affiliations</label><textarea class="control" id="j-certs" name="Certificates or affiliations" placeholder="NAMA Board Certified, AHG Registered Herbalist, professional associations\u2026"></textarea></div>
            <div class="field"><label for="j-since">How many years have you been in practice? *</label><input class="control" id="j-since" name="Years in practice" inputmode="numeric" placeholder="12" required><p class="err">Required.</p></div>
            <div class="field"></div>
            <div class="field full"><label for="j-training">Primary training and educational background *</label><textarea class="control" id="j-training" name="Primary training and education" placeholder="Programme, institution, hours completed." required></textarea><p class="err">Required.</p></div>
            <div class="field full"><label for="j-integrative">Integrative or functional medicine training</label>
              <textarea class="control" id="j-integrative" name="Integrative training" placeholder="e.g. IFM Certified Practitioner, ABOIM board certification, fellowship, coursework and hours."></textarea>
              <p class="hint">Publish exactly what you hold. If you have no formal integrative or functional training, leave this blank \u2014 the listing will say &ldquo;none reported&rdquo; rather than implying otherwise.</p></div>
          </div>
        </section>

        <section class="form-section">
          <h2>Pricing &amp; insurance</h2>
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

        <section class="form-section">
          <h2>Listing description</h2>
          <div class="form-grid">
            <div class="field full"><label for="j-long">Give a description of your practice or business *</label>
              <textarea class="control" id="j-long" name="Listing description" style="min-height:170px" required></textarea>
              <p class="hint"><span id="wordcount">0</span> / 150 words. This appears on your own listing page.</p>
              <p class="err">Required.</p></div>
            <div class="field full"><label for="j-files">Media</label>
              <input class="control file" id="j-files" name="Logo or headshot" type="file"
                     accept="image/png,image/jpeg,image/webp" multiple>
              <p class="hint">Upload your logo and/or headshot \u2014 maximum 2 images, 10 MB each. Square images of 500px or larger work best.</p>
              <p class="err" data-for="files">Choose no more than two images, 10 MB each.</p>
              <p class="hint" id="file-list" style="margin-top:.4rem"></p></div>
          </div>
        </section>

        <section class="form-section internal">
          <h2>Additional questions \u2014 not published</h2>
          <p class="hint" style="margin:-.4rem 0 1.2rem">These answers help us plan the directory. They never appear on your listing or anywhere public.</p>
          <div class="form-grid">
            <div class="field full"><label for="j-size">What is the desired size of your business or practice? *</label><textarea class="control" id="j-size" name="Desired size of practice" placeholder="Days per week, patient or customer numbers, or any other metric." required></textarea><p class="err">Required.</p></div>
            {yesno("openins", "If it became available in your field, would you be open to taking insurance?")}
            {yesno("ehr", "Do you use an EHR? (Electronic Health Records)")}
          </div>
        </section>

        <section class="form-section">
          <h2>Confirmation</h2>
          <label class="check attest" for="j-attest">
            <input type="checkbox" id="j-attest" name="Attestation" value="Agreed" required>
            <span>I confirm that the credentials, licenses, certifications and training I have
            given are accurate and current, that I am entitled to practise as described, and
            that I will notify FindWell Directory if any of it changes, lapses or is suspended.
            I understand my listing states how its credentials were established, and that
            unverified listings are published as reported by me.</span>
          </label>
          <p class="err" data-for="attest">This confirmation is required.</p>
        </section>

        <div style="display:flex;gap:.7rem;flex-wrap:wrap;margin-top:2rem;align-items:center">
          <button class="btn btn-primary" type="submit">Send</button>
          <span class="hint" id="join-msg"></span>
        </div>
      </form>

      <div class="notice" id="join-done" style="display:none;margin-top:2rem">
        <b id="join-done-title">Thank you for your submission.</b>
        <span id="join-done-body"> We will get back to you shortly.</span>
        <p style="margin-top:.8rem" id="join-mail-wrap" hidden><a class="btn btn-dark btn-sm" id="join-mail" href="#">Open in email</a></p>
      </div>
    </div>
  </div>
  <div style="height:3rem"></div>"""
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
    body = f"""  <section class="page-banner">
    {ABOUT_BANNER}
    <div class="wrap page-banner-in">
      <p class="crumb banner-crumb"><a href="/">Home</a> / Who we are</p>
      <h1>Who we are</h1>
      <p class="page-banner-lede">Prevention, transparency, and a direct line between practitioners and the people looking for them.</p>
    </div>
  </section>

  <div class="wrap">
    <div class="section-tight" style="max-width:70ch">
      <p class="lede">FindWell Directory was born out of a simple but urgent mission: to change the conversation around healthcare in our country. Too often, access to healing is filtered through layers of insurance systems, hidden costs, and a pharmaceutical-driven model that doesn't reflect the diverse ways people actually seek wellness. We believe health should be rooted in prevention, transparency, and the empowerment of individuals to choose what works best for their bodies and their lives.</p>

      <p class="lede" style="margin-top:1.1rem">This project grew out of our work with Welliva Health, a new approach to healthcare financing that focuses exclusively on integrative and lifestyle-based care rather than the conventional, pharmaceutical-dependent system. While Welliva is developing an alternative model of coverage, FindWell Directory serves as its natural partner: a platform where providers and patients can connect directly, without middlemen. Here, practitioners openly share their credentials, services, and pricing, while users of the directory help us identify the real needs in communities across the country. Together, this network builds the foundation for a healthcare landscape that values prevention, choice, and trust.</p>

      <aside class="partner">
        <a href="https://wellivahealth.com/" target="_blank" rel="noopener">
          <img src="{WELLIVA_LOGO}" alt="Welliva Health" width="360" height="96" loading="lazy" decoding="async">
        </a>
        <div>
          <p class="partner-lede">Health Assurance for whole-person care.</p>
          <p><a class="partner-link" href="https://wellivahealth.com/" target="_blank" rel="noopener">wellivahealth.com &rarr;</a></p>
        </div>
      </aside>

      <h2 style="font-size:1.35rem;margin:2.6rem 0 .8rem">What we verify</h2>
      <p class="lede">For licensed professions we check the license number against the issuing board and record the date of the check. For unlicensed disciplines there is no board to check, so we record the training programme, hours and any voluntary certification, and we say plainly that no licensure exists.</p>

      <h2 style="font-size:1.35rem;margin:2.4rem 0 .8rem">What we don't do</h2>
      <p class="lede">We don't evaluate clinical claims, host reviews, or vouch for outcomes. A listing here means the credentials are as stated \u2014 nothing more. Complementary care works best alongside medical care, and this directory is built on the assumption that you have a physician too.</p>

      <p style="margin-top:2.4rem"><a class="btn btn-dark" href="/directory/">Browse the directory</a></p>
    </div>
  </div>
  <div style="height:3rem"></div>"""
    return shell("Who we are \u2014 FindWell Directory",
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
        inner = """<div class="empty" style="margin-top:2.4rem">
        <h3>Nothing published yet</h3>
        <p>We are writing about how to choose a practitioner, what licensure does and
        does not guarantee, and what integrative care costs. Check back shortly.</p>
        <p style="margin-top:1.2rem"><a class="btn btn-dark btn-sm" href="/directory/">Find a provider instead</a></p>
      </div>"""
    body = f"""  <div class="wrap">
    <p class="crumb"><a href="/">Home</a> / Articles</p>
    <div class="section-tight">
      <h1 style="font-size:clamp(1.9rem,4vw,2.6rem);margin-bottom:.8rem">Articles</h1>
      <p class="lede">Plain explanations of how holistic and integrative care actually works \u2014 what the credentials mean, what questions to ask, and what things cost.</p>
      {inner}
    </div>
  </div>
  <div style="height:3rem"></div>"""
    return shell("Articles \u2014 FindWell Directory",
                 "Plain explanations of how holistic and integrative care works: credentials, questions to ask, and what care costs.",
                 "/articles/", body)

def page_article(a):
    body = f"""  <div class="wrap">
    <p class="crumb"><a href="/">Home</a> / <a href="/articles/">Articles</a> / {E(a['title'])}</p>
    <article class="section-tight" style="max-width:68ch">
      <h1 style="font-size:clamp(1.9rem,4vw,2.7rem);margin-bottom:.6rem">{E(a['title'])}</h1>
      <p class="crumb" style="padding:0 0 1.6rem">{E(a['date'])}{' \u00b7 ' + E(a['author']) if a.get('author') else ''}</p>
      <div class="prose">{a['body']}</div>
      <p style="margin-top:2.4rem"><a class="btn btn-dark" href="/articles/">All articles</a></p>
    </article>
  </div>
  <div style="height:3rem"></div>"""
    return shell(f"{a['title']} \u2014 FindWell Directory",
                 a.get('summary', '')[:180], f"/articles/{a['slug']}/", body)

def page_advertise():
    body = """  <div class="wrap">
    <p class="crumb"><a href="/">Home</a> / Advertise with us</p>
    <div class="section-tight" style="max-width:70ch">
      <h1 style="font-size:clamp(1.9rem,4vw,2.6rem);margin-bottom:.8rem">Advertise with us</h1>
      <p class="lede">FindWell reaches people at the moment they are choosing a practitioner \u2014 comparing credentials, weighing cost, deciding who to call. If you serve that audience, we would like to hear from you.</p>

      <h2 style="font-size:1.35rem;margin:2.6rem 0 .8rem">What we will never sell</h2>
      <p class="lede">Placement in the directory. Listings are free, ordered by relevance and distance, and no practitioner can pay to rank higher, appear first, or be marked as recommended. We do not sell leads or share the contact details of people using the site. That rule is the reason the directory is worth advertising in at all, and it is not for sale.</p>

      <h2 style="font-size:1.35rem;margin:2.4rem 0 .8rem">What is available</h2>
      <ul class="split-list">
        <li><strong>Sponsored articles.</strong> Clearly labelled, editorially reviewed, and written to be useful rather than promotional.</li>
        <li><strong>Display placements.</strong> On article pages and discipline pages, visually distinct from listings.</li>
        <li><strong>Partnerships.</strong> Schools, professional associations, labs, dispensaries, and insurers building something aligned with integrative care.</li>
      </ul>

      <h2 style="font-size:1.35rem;margin:2.4rem 0 .8rem">Get in touch</h2>
      <p class="lede">Tell us who you are trying to reach and we will tell you honestly whether our audience is a fit. Rates depend on placement and season.</p>
      <p style="margin-top:1.6rem">
        <a class="btn btn-primary" href="mailto:{CONTACT_EMAIL}?subject=Advertising%20enquiry">Email us about advertising</a>
      </p>
    </div>
  </div>
  <div style="height:3rem"></div>"""
    return shell("Advertise with us \u2014 FindWell Directory",
                 "Reach people at the moment they are choosing a holistic practitioner. Sponsored articles, display placements and partnerships \u2014 never paid placement in the directory.",
                 "/advertise/", body)

def page_verification():
    body = """  <div class="wrap">
    <p class="crumb"><a href="/">Home</a> / What verification means</p>
    <div class="section-tight" style="max-width:70ch">
      <h1 style="font-size:clamp(1.9rem,4vw,2.6rem);margin-bottom:.8rem">What verification means here</h1>
      <p class="lede">Every listing says plainly how its credentials were established. There are two states, and neither is a badge.</p>

      <div class="verify-example">
        <p class="verify verify-reported"><b>As reported by the practitioner.</b> Not independently verified.</p>
        <p>The practitioner told us their credentials and we published what they said. We have not checked it with anyone. This is a normal, permanent state for a listing here \u2014 not a queue we are working through.</p>
      </div>

      <div class="verify-example">
        <p class="verify verify-confirmed"><b>License AC-4821 confirmed</b> with the Arizona Acupuncture Board of Examiners, 25 Aug 2026.</p>
        <p>We checked directly with the body that issued the credential, and we name that body and the date we checked. A credential can lapse after a check, which is why the date is there.</p>
      </div>

      <h2 style="font-size:1.35rem;margin:2.6rem 0 .8rem">Three things people confuse</h2>
      <ul class="split-list">
        <li><strong>A state license</strong> is issued by a government board that can revoke it. Naturopathic physicians, acupuncturists, chiropractors, counselors and massage therapists are licensed in Arizona. A license number can be checked against the issuing board by anyone, including you.</li>
        <li><strong>A certification</strong> comes from a private body with its own training requirements and assessment \u2014 NAMA board certification in Ayurveda, NBC-HWC for health coaches. Real, and meaningful, but no government stands behind it and nobody can be struck off a public register.</li>
        <li><strong>A membership</strong> is something you join, usually by paying. It is not a credential, and we do not treat it as one, whatever it is called.</li>
      </ul>

      <h2 style="font-size:1.35rem;margin:2.4rem 0 .8rem">Disciplines with no license at all</h2>
      <p class="lede">Ayurveda, herbalism, energy work and end-of-life support have no state licensure anywhere in the United States. That is not a gap in our checking \u2014 there is no register to check. For those listings we publish the training programme, the hours and any voluntary certification, and we say that no licensure exists.</p>

      <h2 style="font-size:1.35rem;margin:2.4rem 0 .8rem">What practitioners agree to</h2>
      <p class="lede">Everyone who applies confirms that the credentials they give us are accurate and current, and agrees to tell us if anything changes, lapses or is suspended. If you believe a listing is inaccurate, <a href="mailto:info@findwelldirectory.com?subject=Listing%20query">tell us</a> and we will look into it.</p>

      <h2 style="font-size:1.35rem;margin:2.4rem 0 .8rem">What a listing is not</h2>
      <p class="lede">A listing is not a referral, a recommendation, or a judgement about anyone's competence. We publish credentials as stated and, where we have checked them, we say who with and when. Choosing a practitioner remains yours to do.</p>

      <p style="margin-top:2.4rem"><a class="btn btn-dark" href="/directory/">Browse the directory</a></p>
    </div>
  </div>
  <div style="height:3rem"></div>"""
    return shell("What verification means \u2014 FindWell Directory",
                 "How credentials on the FindWell Directory are established: what we check, what we don't, and the difference between a state license, a certification and a paid membership.",
                 "/verification/", body)

def page_404():
    body = """  <div class="wrap section">
    <div class="empty">
      <h3>That page isn't here</h3>
      <p>The link may be out of date, or the listing may have been removed.</p>
      <p style="margin-top:1.2rem"><a class="btn btn-dark btn-sm" href="/directory/">Browse the directory</a></p>
    </div>
  </div>"""
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

    for d in DISCIPLINES:
        rows = [p for p in PROVIDERS if d["key"] in p["categories"]]
        written.append(write(f"practice-types/{d['slug']}/", page_directory(
            subset=rows,
            title=f"{d['label']} practitioners — FindWell Directory",
            desc=f"{d['label']}: {d['note']}",
            path=f"/practice-types/{d['slug']}/",
            heading=d["label"], intro=d["note"],
            trail=[("Home", "/"), ("Disciplines", "/practice-types/"), (d["label"], None)],
            footer_link=("All disciplines", "/practice-types/"))))

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
            footer_link=("All locations", "/locations/"))))

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
