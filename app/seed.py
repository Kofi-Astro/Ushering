"""Populates the database with the original starter content the first time
the app runs against an empty database. After that, the business owner
edits everything through the admin panel — this only ever runs once per
database (each seed function checks the table is empty before inserting).
"""

from sqlalchemy.orm import Session

from .models import FAQItem, GalleryItem, Service, SiteSetting, SiteText, Testimonial
from .site_text_catalog import all_fields

SERVICES = [
    dict(
        title="Wedding Ushering",
        icon="fa-solid fa-ring",
        order=1,
        home_description="Elegant ushers who guide guests, manage seating and keep your ceremony and reception running smoothly.",
        description="Elegant, well-coordinated ushers for your ceremony and reception.",
        highlights="Guest seating & VIP coordination\nProgramme flow support\nGift & guest book management\nBridal party assistance",
    ),
    dict(
        title="Corporate Events",
        icon="fa-solid fa-building",
        order=2,
        home_description="Professional front-of-house support for conferences, product launches, AGMs and brand activations.",
        description="Polished front-of-house teams for conferences, launches and AGMs.",
        highlights="Guest registration & badging\nDelegate assistance\nHall & venue coordination\nBrand-aligned presentation",
    ),
    dict(
        title="Funerals",
        icon="fa-solid fa-dove",
        order=3,
        home_description="Respectful, composed ushering that supports grieving families and guides guests with dignity.",
        description="Respectful, composed ushering for one-week observances and funerals.",
        highlights="Guest reception & seating\nCondolence book management\nFamily & VIP support\nDiscreet crowd coordination",
    ),
    dict(
        title="Conferences",
        icon="fa-solid fa-microphone-lines",
        order=4,
        home_description="Registration desks, delegate assistance and hall coordination for seamless multi-day programmes.",
        description="Seamless registration and hall management for multi-day programmes.",
        highlights="Registration desk staffing\nSession & breakout coordination\nDelegate enquiries\nMaterials & kit distribution",
    ),
    dict(
        title="Birthdays & Parties",
        icon="fa-solid fa-cake-candles",
        order=5,
        home_description="Friendly, energetic ushers who keep celebrations organized and every guest well attended to.",
        description="Friendly, attentive ushers who keep celebrations organized.",
        highlights="Guest welcome & seating\nGift table management\nProgramme coordination\nGuest list & access control",
    ),
    dict(
        title="Concerts & Special Occasions",
        icon="fa-solid fa-music",
        order=6,
        home_description="Crowd flow, access control and guest support for concerts and large public gatherings.",
        description="Access control and crowd flow support for large gatherings.",
        highlights="Ticket & access verification\nCrowd flow management\nVIP & media coordination\nOn-ground guest support",
    ),
    dict(
        title="Churches & Schools",
        icon="fa-solid fa-church",
        order=7,
        home_description="Ongoing or event-based ushering support for congregations, schools and institutions.",
        description="Ongoing or event-based ushering support for congregations and institutions.",
        highlights="Service & event-day ushering\nVisitor welcome & guidance\nProgramme & seating support\nTrained, respectful staff",
    ),
    dict(
        title="Brand Activations",
        icon="fa-solid fa-tags",
        order=8,
        home_description="On-brand hospitality staff for promotions, launches and pop-up events.",
        description="On-brand hospitality staff for promotions, launches and pop-up events.",
        highlights="Brand ambassador presentation\nGuest engagement\nProduct/registration support\nFlexible team sizes",
    ),
    dict(
        title="Custom Event Support",
        icon="fa-solid fa-people-group",
        order=9,
        home_description="Have something unique in mind? We tailor a team and plan to fit your event.",
        description="Have something unique in mind? We tailor a team and plan to fit it.",
        highlights="Custom staffing plans\nUniform & branding options\nEvent-day coordination\nFlexible scheduling",
    ),
]

TESTIMONIALS = [
    dict(
        name="Ama K.",
        role="Bride, Accra",
        rating=5,
        order=1,
        quote="GPS Ushering made our wedding day feel effortless. Every guest was warmly received and the team was so professional.",
    ),
    dict(
        name="Kwame O.",
        role="Event Manager",
        rating=5,
        order=2,
        quote="Our conference registration ran smoothly thanks to their well-trained ushers. Punctual, sharp and reliable.",
    ),
    dict(
        name="Efua T.",
        role="Family Representative",
        rating=5,
        order=3,
        quote="Respectful and composed during a difficult time for our family. We are grateful for their support at the funeral.",
    ),
    dict(
        name="Nana Yaa B.",
        role="HR Manager, Corporate Client",
        rating=5,
        order=4,
        quote="Sharp, well-dressed and organized. Our AGM guests were impressed with how smoothly registration went.",
    ),
    dict(
        name="Kojo M.",
        role="Church Events Coordinator",
        rating=5,
        order=5,
        quote="They have been ushering our anniversary services for two years running. Always punctual and courteous with our congregation.",
    ),
    dict(
        name="Abena O.",
        role="Birthday Celebrant",
        rating=5,
        order=6,
        quote="From gift table to guest seating, everything was handled with a smile. Made my milestone birthday stress-free.",
    ),
]

GALLERY_ITEMS = [
    dict(label="Wedding Ceremony — Accra", category="weddings", order=1),
    dict(label="Wedding Reception Coordination", category="weddings", order=2),
    dict(label="Bridal Party Assistance", category="weddings", order=3),
    dict(label="Corporate Product Launch", category="corporate", order=4),
    dict(label="Brand Activation Team", category="corporate", order=5),
    dict(label="AGM Front-of-House Team", category="corporate", order=6),
    dict(label="Conference Registration Desk", category="conferences", order=7),
    dict(label="Delegate Hall Support", category="conferences", order=8),
    dict(label="Funeral Guest Reception", category="funerals", order=9),
    dict(label="Condolence Book Support", category="funerals", order=10),
    dict(label="Milestone Birthday Celebration", category="parties", order=11),
    dict(label="Private Party Guest Coordination", category="parties", order=12),
]

FAQ_ITEMS = [
    dict(
        question="What areas do you cover?",
        order=1,
        answer="We are based in Accra and provide ushering and event support services across Ghana, including the Greater Accra, Ashanti, Eastern and Central regions. Travel arrangements can be made for events outside our immediate coverage area.",
    ),
    dict(
        question="How far in advance should I book?",
        order=2,
        answer="We recommend booking at least 2–3 weeks before your event to guarantee availability, especially during peak wedding and festive seasons. That said, we do our best to accommodate last-minute and urgent requests where possible.",
    ),
    dict(
        question="Do your ushers wear uniforms?",
        order=3,
        answer="Yes. Our ushers are presented in smart, coordinated attire for every event, and we can adapt our dress code to match your event's colour scheme or theme on request.",
    ),
    dict(
        question="Can you handle large events?",
        order=4,
        answer="Absolutely. We scale our team size to match your guest count and venue, from intimate gatherings of a few dozen guests to large conferences and public events with hundreds of attendees.",
    ),
    dict(
        question="How do I book your services?",
        order=5,
        answer="You can book us by filling out the form on our Book Us page, calling or messaging us on WhatsApp, or emailing us directly. We'll follow up to discuss your event details and confirm your booking.",
    ),
    dict(
        question="What is your payment structure?",
        order=6,
        answer="We typically require a deposit to confirm your booking, with the remaining balance due before or on the day of your event. Full payment terms are shared once your event scope is confirmed.",
    ),
    dict(
        question="Can I customize the number of ushers?",
        order=7,
        answer="Yes. We recommend a team size based on your guest count and venue layout, and we're happy to adjust the number of ushers to fit your budget and specific requirements.",
    ),
    dict(
        question="Do you offer services outside Accra?",
        order=8,
        answer="Yes, we serve clients across Ghana. For events outside the Greater Accra Region, a travel and accommodation allowance may apply depending on distance — this is agreed upfront before booking.",
    ),
]


def seed_if_empty(db: Session) -> None:
    """Called once at startup (see app/main.py). Each table is checked and
    seeded independently, so if the business owner has already added
    content to one table (say, added their own testimonial) but another
    table is somehow still empty, only the empty one gets the starter
    data — nothing already saved is ever overwritten or duplicated."""
    if db.query(Service).count() == 0:
        db.add_all(Service(**data) for data in SERVICES)
    if db.query(Testimonial).count() == 0:
        db.add_all(Testimonial(**data) for data in TESTIMONIALS)
    if db.query(GalleryItem).count() == 0:
        db.add_all(GalleryItem(**data) for data in GALLERY_ITEMS)
    if db.query(FAQItem).count() == 0:
        db.add_all(FAQItem(**data) for data in FAQ_ITEMS)
    if db.query(SiteSetting).count() == 0:
        db.add(SiteSetting(id=1))
    if db.query(SiteText).count() == 0:
        db.add_all(SiteText(key=f.key, value=f.default) for f in all_fields())
    db.commit()
