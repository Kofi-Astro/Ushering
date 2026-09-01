"""Single source of truth for every piece of free-form copy on the
public site that isn't already a Service / Testimonial / GalleryItem /
FAQItem / SiteSetting field — headings, paragraphs, button labels,
section eyebrows and similar wording baked into the page templates. See
app/models.py:SiteText for the table this seeds and app/content.py:
get_site_text for how templates read it back.

Grouped by which admin "Page Text" section each field appears under (see
app/admin/routers/site_text.py) and, within a group, by where it sits on
the page. Keeping this catalog in one file means app/seed.py's starter
values, the admin form's fields, and the actual template lookups all stay
in sync — there's nowhere else a key could quietly drift.

A handful of keys are deliberately shared across more than one spot in
the templates: nav.*_label is used for a page's navbar link, its footer
"Quick Links" entry, and its own breadcrumb crumb, since those three are
the same navigational destination shown three times rather than three
independent pieces of content — editing "About Us" once should rename it
everywhere. Everything else that happens to repeat by coincidence (e.g.
several unrelated "Book Us Now" buttons) keeps its own independent key,
since a business owner might reasonably want different wording in
different sections.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TextField:
    key: str
    label: str
    default: str
    long: bool = False  # False -> <input type="text">, True -> <textarea>


@dataclass(frozen=True)
class TextGroup:
    title: str
    fields: list[TextField] = field(default_factory=list)


GROUPS: dict[str, TextGroup] = {
    "navigation": TextGroup(
        title="Navigation & Footer",
        fields=[
            TextField("nav.home_label", "Home (navbar link)", "Home"),
            TextField("nav.about_label", "About Us (navbar link, footer, breadcrumb)", "About Us"),
            TextField("nav.services_label", "Services (navbar link, footer, breadcrumb)", "Services"),
            TextField("nav.gallery_label", "Gallery (navbar link, footer, breadcrumb)", "Gallery"),
            TextField("nav.testimonials_label", "Testimonials (navbar link, footer, breadcrumb)", "Testimonials"),
            TextField("nav.faq_label", "FAQ (navbar link, footer, breadcrumb)", "FAQ"),
            TextField("nav.book_us_label", "Book Us (navbar link, footer, breadcrumb)", "Book Us"),
            TextField("nav.cta_label", "Book Us Now (navbar button)", "Book Us Now"),
            TextField("footer.facebook_handle_label", "Footer Facebook handle label", "Facebook"),
            TextField("footer.instagram_handle_label", "Footer Instagram handle label", "Instagram"),
            TextField("footer.tiktok_handle_label", "Footer TikTok handle label", "TikTok"),
            TextField("footer.blurb", "Footer about blurb", "Professional ushering and event support services for weddings, corporate events, funerals, conferences and special occasions across Ghana.", long=True),
            TextField("footer.quick_links_heading", "Footer \"Quick Links\" column heading", "Quick Links"),
            TextField("footer.services_heading", "Footer \"Services\" column heading", "Services"),
            TextField("footer.contact_heading", "Footer \"Contact\" column heading", "Contact"),
            TextField("footer.copyright_suffix", "Footer copyright line (after the year and business name)", "All rights reserved."),
        ],
    ),
    "home": TextGroup(
        title="Homepage",
        fields=[
            TextField("home.hero.eyebrow", "Hero eyebrow", "Ushering & Event Support Services"),
            TextField("home.hero.title", "Hero heading", "Elegant, Reliable Ushering for Your Most Important Events"),
            TextField("home.hero.lead", "Hero paragraph", "GPS Ushering and Events delivers polished guest coordination, hospitality and registration support for weddings, corporate events, funerals, conferences, birthdays, concerts and special occasions across Ghana.", long=True),
            TextField("home.hero.cta_primary", "Hero button 1", "Book Us Now"),
            TextField("home.hero.cta_secondary", "Hero button 2", "View Our Services"),
            TextField("home.hero.stat1_number", "Stat 1 number", "500+"),
            TextField("home.hero.stat1_label", "Stat 1 label", "Events Covered"),
            TextField("home.hero.stat2_number", "Stat 2 number", "100+"),
            TextField("home.hero.stat2_label", "Stat 2 label", "Trained Ushers"),
            TextField("home.hero.stat3_number", "Stat 3 number", "10+"),
            TextField("home.hero.stat3_label", "Stat 3 label", "Regions Served"),
            TextField("home.about.eyebrow", "\"Who We Are\" eyebrow", "Who We Are"),
            TextField("home.about.title", "\"Who We Are\" heading", "Professionalism, Elegance & Excellent Customer Service"),
            TextField("home.about.paragraph", "\"Who We Are\" paragraph", "GPS Ushering and Events is a Ghana-based ushering and event support company trusted by event planners, corporate organizations, couples, funeral organizers, schools, churches and brands. We ensure every guest feels welcomed, informed and taken care of, from arrival to departure.", long=True),
            TextField("home.about.checklist1", "\"Who We Are\" checklist item 1", "Smooth guest coordination and crowd management"),
            TextField("home.about.checklist2", "\"Who We Are\" checklist item 2", "Warm, professional hospitality at every touchpoint"),
            TextField("home.about.checklist3", "\"Who We Are\" checklist item 3", "Efficient registration and check-in assistance"),
            TextField("home.about.checklist4", "\"Who We Are\" checklist item 4", "Trained, uniformed and well-presented staff"),
            TextField("home.about.cta", "\"Who We Are\" button", "More About Us"),
            TextField("home.about.media_note", "Photo placeholder note", "Photo of our ushering team — to be added"),
            TextField("home.services.eyebrow", "Services section eyebrow", "What We Offer"),
            TextField("home.services.title", "Services section heading", "Our Services"),
            TextField("home.services.intro", "Services section intro", "From intimate ceremonies to large-scale conferences, our team is trained to handle every type of event with grace and precision.", long=True),
            TextField("home.services.cta", "Services section button", "See All Services"),
            TextField("home.gallery.eyebrow", "Gallery section eyebrow", "Our Gallery"),
            TextField("home.gallery.title", "Gallery section heading", "Moments From Our Events"),
            TextField("home.gallery.intro", "Gallery section intro", "A glimpse of the weddings, corporate events and celebrations our team has proudly supported.", long=True),
            TextField("home.gallery.cta", "Gallery section button", "View Full Gallery"),
            TextField("home.testimonials.eyebrow", "Testimonials section eyebrow", "Client Love"),
            TextField("home.testimonials.title", "Testimonials section heading", "What Our Clients Say"),
            TextField("home.cta.title", "Bottom CTA heading", "Ready to Plan Your Next Event?"),
            TextField("home.cta.paragraph", "Bottom CTA paragraph", "Let our professional ushers take care of your guests while you focus on what matters most.", long=True),
            TextField("home.cta.book_button", "Bottom CTA \"Book Us Now\" button", "Book Us Now"),
            TextField("home.cta.whatsapp_button", "Bottom CTA WhatsApp button", "WhatsApp"),
            TextField("home.cta.facebook_button", "Bottom CTA Facebook button", "Facebook"),
            TextField("home.cta.instagram_button", "Bottom CTA Instagram button", "Instagram"),
            TextField("home.cta.tiktok_button", "Bottom CTA TikTok button", "TikTok"),
        ],
    ),
    "about": TextGroup(
        title="About Page",
        fields=[
            TextField("about.hero.eyebrow", "Hero eyebrow", "About Us"),
            TextField("about.hero.title", "Hero heading", "The Team Behind Your Seamless Event"),
            TextField("about.media_note", "Photo placeholder note", "Team / event photo — to be added"),
            TextField("about.story.eyebrow", "Story section eyebrow", "Our Story"),
            TextField("about.story.title", "Story section heading", "Built on Professionalism & Genuine Hospitality"),
            TextField("about.story.paragraph1", "Story paragraph 1", "GPS Ushering and Events was founded to bring order, elegance and warmth to events across Ghana. What began as a small team of dedicated ushers has grown into a trusted service for event planners, corporate organizations, couples, funeral organizers, schools, churches and brands.", long=True),
            TextField("about.story.paragraph2", "Story paragraph 2", "We believe that the first face a guest sees sets the tone for the entire event — so we train every usher to combine sharp presentation with genuine hospitality, ensuring each guest feels welcomed, guided and valued from arrival to departure.", long=True),
            TextField("about.story.cta", "Story section button", "Work With Us"),
            TextField("about.values.eyebrow", "Mission/Vision eyebrow", "Mission & Vision"),
            TextField("about.values.title", "Mission/Vision heading", "What Drives Us"),
            TextField("about.values.mission_title", "\"Our Mission\" card title", "Our Mission"),
            TextField("about.values.mission_body", "\"Our Mission\" card body", "To deliver smooth guest coordination and outstanding hospitality that elevates every event we support.", long=True),
            TextField("about.values.vision_title", "\"Our Vision\" card title", "Our Vision"),
            TextField("about.values.vision_body", "\"Our Vision\" card body", "To be Ghana's most trusted name in professional ushering and event support services.", long=True),
            TextField("about.values.promise_title", "\"Our Promise\" card title", "Our Promise"),
            TextField("about.values.promise_body", "\"Our Promise\" card body", "Punctual, well-presented and courteous staff at every event, every time.", long=True),
            TextField("about.values.values_title", "\"Our Values\" card title", "Our Values"),
            TextField("about.values.values_body", "\"Our Values\" card body", "Professionalism, elegance, reliability and heartfelt customer service guide everything we do.", long=True),
            TextField("about.why.eyebrow", "Why Choose Us eyebrow", "Why Choose Us"),
            TextField("about.why.title", "Why Choose Us heading", "What Sets GPS Ushering Apart"),
            TextField("about.why.card1_title", "Feature card 1 title", "Trained & Presentable Staff"),
            TextField("about.why.card1_body", "Feature card 1 body", "Every usher is trained in etiquette, guest handling and event protocol, and presented in smart, coordinated attire.", long=True),
            TextField("about.why.card2_title", "Feature card 2 title", "Punctual & Reliable"),
            TextField("about.why.card2_body", "Feature card 2 body", "We arrive early, brief thoroughly and stay composed under pressure so your event runs on time.", long=True),
            TextField("about.why.card3_title", "Feature card 3 title", "Tailored to Your Event"),
            TextField("about.why.card3_body", "Feature card 3 body", "From intimate gatherings to large conferences, we scale our team and approach to fit your specific needs.", long=True),
            TextField("about.why.card4_title", "Feature card 4 title", "Clear Communication"),
            TextField("about.why.card4_body", "Feature card 4 body", "From your first inquiry to the final guest departure, we keep you informed every step of the way.", long=True),
            TextField("about.why.card5_title", "Feature card 5 title", "Discreet & Respectful"),
            TextField("about.why.card5_body", "Feature card 5 body", "We handle sensitive occasions, including funerals, with the utmost dignity and discretion.", long=True),
            TextField("about.why.card6_title", "Feature card 6 title", "Nationwide Coverage"),
            TextField("about.why.card6_body", "Feature card 6 body", "Based in Accra and available to support events across Ghana.", long=True),
            TextField("about.cta.title", "Bottom CTA heading", "Let's Make Your Event Unforgettable"),
            TextField("about.cta.paragraph", "Bottom CTA paragraph", "Tell us about your event and we'll put together the right team for you.", long=True),
            TextField("about.cta.button", "Bottom CTA button", "Book Us Now"),
        ],
    ),
    "services": TextGroup(
        title="Services Page",
        fields=[
            TextField("services.hero.eyebrow", "Hero eyebrow", "Our Services"),
            TextField("services.hero.title", "Hero heading", "Ushering & Event Support for Every Occasion"),
            TextField("services.how.eyebrow", "\"How It Works\" eyebrow", "How It Works"),
            TextField("services.how.title", "\"How It Works\" heading", "Booking Us Is Simple"),
            TextField("services.how.step1_title", "Step 1 title", "Inquire"),
            TextField("services.how.step1_body", "Step 1 body", "Reach out via our booking form, call or WhatsApp with your event details.", long=True),
            TextField("services.how.step2_title", "Step 2 title", "Consult"),
            TextField("services.how.step2_body", "Step 2 body", "We discuss your event, guest count and specific needs to plan the right team.", long=True),
            TextField("services.how.step3_title", "Step 3 title", "Confirm"),
            TextField("services.how.step3_body", "Step 3 body", "We agree on scope, staffing and schedule, then confirm your booking.", long=True),
            TextField("services.how.step4_title", "Step 4 title", "Deliver"),
            TextField("services.how.step4_body", "Step 4 body", "Our trained ushers arrive early and deliver a smooth, professional event.", long=True),
            TextField("services.cta.title", "Bottom CTA heading", "Not Sure Which Service You Need?"),
            TextField("services.cta.paragraph", "Bottom CTA paragraph", "Tell us about your event and we'll recommend the right package for you.", long=True),
            TextField("services.cta.button", "Bottom CTA button", "Get In Touch"),
        ],
    ),
    "book_us": TextGroup(
        title="Book Us Page",
        fields=[
            TextField("book_us.hero.eyebrow", "Hero eyebrow", "Book Us"),
            TextField("book_us.hero.title", "Hero heading", "Let's Plan Your Event Together"),
            TextField("book_us.success_message", "Form success message", "Thank you! Your booking request has been received. We'll be in touch shortly.", long=True),
            TextField("book_us.form.title", "Form card heading", "Request a Booking"),
            TextField("book_us.form.intro", "Form card intro", "Fill in your event details below and our team will get back to you within 24 hours.", long=True),
            TextField("book_us.form.location_placeholder", "Location field placeholder", "Venue and city/town"),
            TextField("book_us.form.location_hint", "Location field hint", "Click or drag the pin on the map to your venue and we'll fill this in for you — or just type it in directly.", long=True),
            TextField("book_us.form.message_placeholder", "Message field placeholder", "Number of ushers needed, special requirements, etc."),
            TextField("book_us.form.submit_button", "Submit button", "Submit Booking Request"),
            TextField("book_us.form.disclaimer", "Consent/disclaimer note", "By submitting this form, you agree to be contacted by GPS Ushering and Events regarding your inquiry.", long=True),
            TextField("book_us.contact.title", "Contact card heading", "Contact Details"),
            TextField("book_us.contact.call_label", "\"Call Us\" label", "Call Us"),
            TextField("book_us.contact.whatsapp_label", "\"WhatsApp\" label", "WhatsApp"),
            TextField("book_us.contact.email_label", "\"Email\" label", "Email"),
            TextField("book_us.contact.location_label", "\"Location\" label", "Location"),
            TextField("book_us.contact.whatsapp_cta", "WhatsApp link text", "Chat With Us"),
        ],
    ),
    "faq": TextGroup(
        title="FAQ Page",
        fields=[
            TextField("faq.hero.eyebrow", "Hero eyebrow", "FAQ"),
            TextField("faq.hero.title", "Hero heading", "Frequently Asked Questions"),
            TextField("faq.cta.title", "Bottom CTA heading", "Still Have Questions?"),
            TextField("faq.cta.paragraph", "Bottom CTA paragraph", "Reach out and we'll be happy to help you plan your event.", long=True),
            TextField("faq.cta.contact_button", "Bottom CTA \"Contact Us\" button", "Contact Us"),
            TextField("faq.cta.whatsapp_button", "Bottom CTA WhatsApp button", "WhatsApp"),
            TextField("faq.cta.facebook_button", "Bottom CTA Facebook button", "Facebook"),
            TextField("faq.cta.instagram_button", "Bottom CTA Instagram button", "Instagram"),
            TextField("faq.cta.tiktok_button", "Bottom CTA TikTok button", "TikTok"),
        ],
    ),
    "gallery": TextGroup(
        title="Gallery Page",
        fields=[
            TextField("gallery.hero.eyebrow", "Hero eyebrow", "Gallery"),
            TextField("gallery.hero.title", "Hero heading", "Moments From Events We've Proudly Supported"),
            TextField("gallery.filter.all", "Filter button: All", "All"),
            TextField("gallery.filter.weddings", "Filter button: Weddings", "Weddings"),
            TextField("gallery.filter.corporate", "Filter button: Corporate", "Corporate"),
            TextField("gallery.filter.funerals", "Filter button: Funerals", "Funerals"),
            TextField("gallery.filter.conferences", "Filter button: Conferences", "Conferences"),
            TextField("gallery.filter.parties", "Filter button: Birthdays & Parties", "Birthdays & Parties"),
            TextField("gallery.cta.title", "Bottom CTA heading", "Want Photos Like These From Your Event?"),
            TextField("gallery.cta.paragraph", "Bottom CTA paragraph", "Book our team and let us help create a memorable, well-run experience for your guests.", long=True),
            TextField("gallery.cta.button", "Bottom CTA button", "Book Us Now"),
        ],
    ),
    "testimonials": TextGroup(
        title="Testimonials Page",
        fields=[
            TextField("testimonials.hero.eyebrow", "Hero eyebrow", "Testimonials"),
            TextField("testimonials.hero.title", "Hero heading", "What Our Clients Say About Us"),
            TextField("testimonials.cta.title", "Bottom CTA heading", "Ready to Become Our Next Happy Client?"),
            TextField("testimonials.cta.paragraph", "Bottom CTA paragraph", "Let's give your guests the same experience.", long=True),
            TextField("testimonials.cta.button", "Bottom CTA button", "Book Us Now"),
        ],
    ),
}


def all_fields() -> list[TextField]:
    """Every TextField across every group, flattened — used by
    app/seed.py to seed the whole catalog in one pass without needing to
    know the group structure."""
    return [f for group in GROUPS.values() for f in group.fields]
