"""RAG Knowledge Base — Real Pebble product knowledge scraped from pebble.prod.xenvoice.com

All content sourced directly from the official Pebble website.
Used by CallAnsweringAgent and AutoReplyAgent to answer questions accurately.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Real Pebble knowledge — sourced from pebble.prod.xenvoice.com
# ---------------------------------------------------------------------------
PEBBLE_KNOWLEDGE_DOCS = [
    {
        "id": "what_is_pebble",
        "content": """Pebble is an AI-native POS (Point of Sale) platform built for restaurants and retail 
        stores/businesses. Pebble connects ordering, loyalty, reviews, campaigns, marketing, and AI tools 
        into one system. It manages sales, customers, and operations while using AI to automate tasks, 
        increase efficiency, and drive smarter decisions. The tagline is: 
        "Sell Anywhere. Manage Everything. One Platform." 
        In-store, online, phone, and delivery orders plus loyalty, reviews, and marketing — 
        all running from a single screen. Website: https://pebble.prod.xenvoice.com
        Phone: (469)-310-7731. Email: customercare@pebbletab.com""",
    },
    {
        "id": "pebble_pos",
        "content": """Pebble POS is a modern point-of-sale system built for faster checkout, cleaner 
        operations, and better visibility. Key stats: 40% faster checkout, 99.5% system uptime. 
        Features include: fast checkout with split payments, table management for restaurants, 
        inventory tracking, staff management, offline mode so you never lose a sale, 
        kitchen display system (KDS) integration, receipt printing and digital receipts, 
        multi-location support from one dashboard. Works for QSR, pizza shops, fine dining, 
        casual dining, food trucks, steakhouses, liquor stores, cafes, bakeries, and more.""",
    },
    {
        "id": "pebble_direct",
        "content": """Pebble Direct lets customers order straight from your website, QR codes, and direct 
        channels so you keep more margin and own every customer relationship from day one. 
        Stop paying 30% commissions to marketplaces like DoorDash and Uber Eats on every order. 
        Pebble Direct gives customers a simple way to order from you directly so you keep the profit, 
        the data, and the relationship. Includes: commission-free ordering from your website, 
        QR code ordering, WhatsApp ordering, branded mobile app, online ordering with delivery.""",
    },
    {
        "id": "pebble_loyalty",
        "content": """Pebble Loyalty rewards customers across in-store and online purchases with one 
        connected loyalty program that drives repeat visits and increases how much they spend over time. 
        Features: points-based rewards, punch card system, birthday rewards, centralized loyalty 
        across all channels, referral programs, promotions and coupons. 
        Result: Golden Indian Cuisine saw 19% increase in repeat orders after switching to Pebble. 
        Customers earn and redeem rewards whether they order in store, online, or through the app.""",
    },
    {
        "id": "pebble_ai",
        "content": """Pebble AI answers calls, takes orders, recovers missed sales, and handles routine 
        tasks so your team can focus on customers instead of being buried in busywork. 
        AI features include:
        - AI Order Taking: AI handles phone orders automatically, 90-100% call coverage
        - AI Phone Ordering: Answer calls, capture orders, reduce missed revenue automatically  
        - AI Reservation: Automated scheduling and reservation management
        - AI Marketer: Automate campaigns, reviews, local SEO, and customer visibility
        - AI Win-Back Agent: Bring back lost customers automatically
        - AI Repeat Customer Agent: Personalized offers for returning customers
        - AI Loyalty Manager: Automated loyalty rewards and retention
        - AI Demand Forecaster: Smart inventory predictions prevent stockouts
        - AI Campaigner: Automated marketing campaigns for repeat customers
        - AI Live Chat: Real-time website chat assistance
        - AI Outreach Agent: Smart customer acquisition and re-engagement
        - AI Reviewer: Automated review requests and monitoring
        - Missed Call Recovery: Turn missed calls into orders automatically
        - After-Hours Coverage: Always available customer phone support
        Result: Applejacks Liquor went from missing calls to 95% calls answered.""",
    },
    {
        "id": "pebble_marketing",
        "content": """Pebble Marketing shows up when local customers search for businesses like yours. 
        Pebble handles SEO, online visibility, and paid ads so new customers find you before competitors.
        Features:
        - AEO & SEO Powered Website: Search-optimized website for local visibility, ranks on Google and AI search
        - Paid Ads: Targeted ads that drive real sales
        - Email & Text Campaigns: Targeted campaigns that drive returns
        - Social Media Posting: Automated multi-platform social media management
        - Google My Business Optimization: Local search visibility optimization
        - Social Media Profile Optimization: Professional profiles that build trust
        - Digital Marketing: Online promotion and customer attraction tools
        - Local Visibility: Get found by local customers""",
    },
    {
        "id": "pebble_campaigns",
        "content": """Pebble Campaigns sends targeted email and text campaigns based on real customer 
        activity so your promotions, reminders, and win-back offers actually land and drive repeat sales.
        Features: email campaigns, text/SMS automation, promotions and coupons, referral programs, 
        flyers to turn walk-ins into repeat digital customers, automated win-back campaigns.
        Send the right offer to the right customer at the right time based on real purchase behavior.""",
    },
    {
        "id": "pebble_reviews",
        "content": """Pebble Reviews automatically collects more reviews after every purchase, responds 
        faster to feedback, and builds the kind of online reputation that brings in new customers daily.
        Features: automated review collection, review and reputation management, 
        respond to Google and Yelp reviews from one place, monitor all reviews centrally.
        People check reviews before they walk in — Pebble helps you collect more reviews consistently 
        and respond quickly.""",
    },
    {
        "id": "pebble_connect",
        "content": """Pebble Connect manages calls, texts, and customer conversations from one place 
        so your team never misses a message and every interaction stays organized and easy to track.
        Features: business phone (VoIP cloud phone system), business texting, 
        call deflection (reduce phone interruptions by answering routine calls automatically),
        unified inbox for all customer communications, CRM (centralized customer relationship management).""",
    },
    {
        "id": "pebble_dash",
        "content": """Pebble Dash pulls marketplace orders, website orders, and phone orders into one 
        screen so your team stops juggling tablets and starts fulfilling faster with fewer mistakes.
        Features: order consolidation (all orders in one dashboard), automatic POS injection 
        (Uber Eats, DoorDash, Grubhub orders flow directly into your POS), 
        menu management and mapping (change prices on all platforms from one screen), 
        smart kitchen routing, order monitoring across all channels.""",
    },
    {
        "id": "pebble_ops",
        "content": """Pebble Ops handles scheduling, time tracking, and payroll from one system so you 
        spend less time on admin and more time running the parts of your business that matter.
        Features: time clock and employee scheduling, payroll (automated payroll processing), 
        hiring (post jobs and manage applicants digitally), workflow automation, 
        daily summaries (automated daily business performance reports), 
        KYB Know Your Business (daily business summaries delivered automatically),
        inventory awareness (real-time stock tracking), issue resolution.""",
    },
    {
        "id": "pebble_hardware",
        "content": """Pebble Hardware lineup:
        - Pebble Core: Your central command station (main POS terminal)
        - Pebble View: Customer-facing display system
        - Pebble Hub: Self-service ordering kiosk
        - Pebble Mini: Compact self-order terminal
        - Pebble Pay: Tap, swipe, and chip ready (payment terminal)
        - Pebble Go: Handheld orders anywhere (mobile ordering device)
        All hardware available at: https://pebble.prod.xenvoice.com/hardware""",
    },
    {
        "id": "pebble_business_types",
        "content": """Pebble works for many business types:
        Restaurants: QSR (Quick Service), Pizza Shops, Fine Dining, Casual Dining, Fast Casual, 
        Full-Service Restaurant, Food Trucks, Steakhouses, Cafes & Coffee Shops, Bakeries, 
        Bagel Shops, Dessert Shops, Ice Cream Shops, Juice & Smoothie Bars, Bars & Pubs, 
        Deli Shops, Ghost Kitchens / Virtual Kitchens.
        Retail: Liquor Stores, Tobacco Shops, Smoke Shops, Vape Stores, CBD Stores, 
        Beauty Stores, Gift Shops, Grocery Stores, Mini Markets / Convenience Stores, 
        Specialty Retail, Boutique Retail, Pet Supply Stores.""",
    },
    {
        "id": "pebble_results_testimonials",
        "content": """Real results from Pebble customers:
        - Applejacks Liquor: 95% calls answered. "We get slammed on Friday and Saturday nights. 
          Before Pebble, we were missing calls left and right. Now every call gets picked up, 
          orders come in automatically."
        - Golden Indian Cuisine: 19% increase in repeat orders. "Our regulars used to order through 
          DoorDash even though they live five minutes away. Now they order direct from our site, 
          we keep the margin, and the loyalty program gives them a reason to come back every week."
        - Oak Ridge Grill (Ben Hartley, Owner): "Pebble brought our orders, delivery, phones, and 
          reporting into one system. Operations feel simpler and more controlled."
        Platform stats: 40% faster checkout, 99.5% system uptime, 90-100% call coverage, 
        replaces the whole stack (1 platform instead of 5 tools).""",
    },
    {
        "id": "pebble_demo_contact",
        "content": """To book a demo with Pebble:
        - Book online: https://pebble.prod.xenvoice.com/book-a-demo
        - Demos are 15-30 minutes, done over video call, completely free with no obligation
        - Available times: 9am-5pm, Monday-Friday
        - Choose a Growth Expert or Sales Consultant
        Contact Pebble:
        - Phone: (469)-310-7731
        - Email: customercare@pebbletab.com
        - Website: https://pebble.prod.xenvoice.com
        - LinkedIn: linkedin.com/company/pebble-pos
        - Facebook: facebook.com/pebblepos1
        - Instagram: instagram.com/pebble_pos""",
    },
    {
        "id": "pebble_why_switch",
        "content": """Why businesses switch to Pebble:
        Problem: Disconnected tools slow you down and cost you customers every day.
        - Customers leave and never come back without an easy way to reorder or earn rewards
        - One-time buyers stay one-time buyers without connected loyalty and campaigns
        - Five separate tools (POS, ordering, marketing, loyalty, reviews) means duplicate work and conflicting data
        - Growth creates more chaos without connected tools and automation
        
        Pebble solution: One system that actually grows your business.
        - Every missed call is a missed sale — Pebble AI answers every call and takes orders
        - Customers forget you unless you remind them — Pebble sends targeted campaigns automatically
        - Stop paying 30% to marketplaces — Pebble Direct lets customers order from you directly
        - Your reputation is your best marketing — Pebble collects reviews consistently
        - One system, zero guesswork — POS, ordering, loyalty, reviews, campaigns, and AI all connected""",
    },
    {
        "id": "pebble_integrations_ordering",
        "content": """Pebble integrations and ordering channels:
        Marketplace integrations: DoorDash, Uber Eats, Grubhub — orders inject directly into POS automatically
        Direct ordering: Website ordering, QR code ordering, WhatsApp ordering, branded mobile app
        Payment: All major payment processors, Apple Pay, Google Pay, tap/swipe/chip
        Marketing: Email campaigns, SMS/text campaigns, social media management
        Operations: Payroll, time tracking, employee scheduling, hiring
        Analytics: Advanced analytics, daily summaries, sales reporting
        All channels managed from one unified dashboard.""",
    },
    {
        "id": "pebble_growth_engine",
        "content": """Pebble Growth Engine: Attract, convert, and grow your customers.
        The complete growth stack for modern retail businesses. Pebble brings together POS, 
        direct ordering, loyalty, marketing, reviews, and AI into one connected platform, 
        so local businesses can sell everywhere, attract new customers, and turn first-time 
        buyers into loyal regulars.
        
        Legacy systems keep the lights on. Pebble helps you fill more seats, move more product, 
        bring customers back, and make better decisions every single day.
        
        Partner program: https://pebble.prod.xenvoice.com/become-a-partner
        Refer a business: https://pebble.prod.xenvoice.com/refer-a-business""",
    },
]


class RAGKnowledgeBase:
    """ChromaDB-backed knowledge base with real Pebble website content.

    Embeds product docs on first load, then retrieves relevant chunks
    for any inbound question using semantic similarity search.
    """

    COLLECTION_NAME = "pebble_knowledge_v2"

    def __init__(self, persist_dir: str = "./chroma_db") -> None:
        self._persist_dir = persist_dir
        self._collection = None
        self._initialized = False

    def initialize(self) -> None:
        """Load or create the ChromaDB collection with real Pebble docs."""
        if self._initialized:
            return
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            client = chromadb.PersistentClient(path=self._persist_dir)
            ef = embedding_functions.DefaultEmbeddingFunction()

            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )

            # Seed docs if collection is empty
            if self._collection.count() == 0:
                logger.info("Seeding RAG with %d real Pebble docs...", len(PEBBLE_KNOWLEDGE_DOCS))
                self._collection.add(
                    ids=[doc["id"] for doc in PEBBLE_KNOWLEDGE_DOCS],
                    documents=[doc["content"] for doc in PEBBLE_KNOWLEDGE_DOCS],
                    metadatas=[{"source": doc["id"]} for doc in PEBBLE_KNOWLEDGE_DOCS],
                )
                logger.info("✅ RAG knowledge base ready with real Pebble content (%d docs)", len(PEBBLE_KNOWLEDGE_DOCS))
            else:
                logger.info("✅ RAG knowledge base loaded (%d docs)", self._collection.count())

            self._initialized = True

        except Exception as e:
            logger.warning("ChromaDB unavailable, using keyword fallback: %s", e)
            self._initialized = False

    def retrieve(self, query: str, top_k: int = 3) -> str:
        """Retrieve top-k relevant Pebble knowledge chunks for a query."""
        if not self._initialized or self._collection is None:
            return self._fallback_retrieve(query)

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, len(PEBBLE_KNOWLEDGE_DOCS)),
            )
            docs = results.get("documents", [[]])[0]
            if not docs:
                return self._fallback_retrieve(query)

            context = "\n\n".join([f"[Pebble Knowledge]: {doc}" for doc in docs])
            logger.debug("RAG retrieved %d chunks for: %s", len(docs), query[:50])
            return context

        except Exception as e:
            logger.warning("RAG retrieval failed: %s", e)
            return self._fallback_retrieve(query)

    def _fallback_retrieve(self, query: str) -> str:
        """Keyword-based fallback when ChromaDB is unavailable."""
        query_lower = query.lower()
        scored = []
        for doc in PEBBLE_KNOWLEDGE_DOCS:
            words = set(query_lower.split())
            doc_words = set(doc["content"].lower().split())
            overlap = len(words & doc_words)
            if overlap > 0:
                scored.append((overlap, doc["content"]))

        scored.sort(reverse=True)
        top = [content for _, content in scored[:3]]
        if top:
            return "\n\n".join([f"[Pebble Knowledge]: {c}" for c in top])

        # Return general overview if nothing matches
        return f"[Pebble Knowledge]: {PEBBLE_KNOWLEDGE_DOCS[0]['content']}"


# Module-level singleton
_rag_kb: Optional[RAGKnowledgeBase] = None


def get_rag_knowledge_base() -> RAGKnowledgeBase:
    """Return the singleton RAG knowledge base, initializing on first call."""
    global _rag_kb
    if _rag_kb is None:
        _rag_kb = RAGKnowledgeBase()
        _rag_kb.initialize()
    return _rag_kb
