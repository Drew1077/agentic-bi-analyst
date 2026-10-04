"""
Agentic BI Analyst
Synthetic E-commerce Dataset Generator

Chat 02 — Dataset Design & Generation
"""

from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 20260915

START_DATE = "2024-01-01"
END_DATE = "2026-08-31"

CUSTOMER_COUNT = 20_000
PRODUCT_COUNT = 2_000
STORE_COUNT = 63
ORDER_COUNT = 150_000

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# RANDOM GENERATORS
# ============================================================

rng = np.random.default_rng(SEED)

fake = Faker("en_IN")
fake.seed_instance(SEED)


# ============================================================
# HELPER FUNCTION
# ============================================================

def random_dates(start_date, end_date, size):
    """Generate deterministic random dates between two dates."""
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    days = (end - start).days

    random_days = rng.integers(
        0,
        days + 1,
        size=size
    )

    return start + pd.to_timedelta(random_days, unit="D")


# ============================================================
# CALENDAR GENERATION
# ============================================================

def generate_calendar():
    """Generate the business calendar dimension."""

    dates = pd.date_range(
        start=START_DATE,
        end=END_DATE,
        freq="D"
    )

    calendar = pd.DataFrame({
        "date": dates
    })

    calendar["day"] = calendar["date"].dt.day
    calendar["month"] = calendar["date"].dt.month
    calendar["month_name"] = calendar["date"].dt.month_name()
    calendar["quarter"] = calendar["date"].dt.quarter
    calendar["year"] = calendar["date"].dt.year
    calendar["week"] = calendar["date"].dt.isocalendar().week.astype(int)
    calendar["day_name"] = calendar["date"].dt.day_name()
    calendar["is_weekend"] = calendar["date"].dt.dayofweek >= 5

    # --------------------------------------------------------
    # Indian business holidays / events
    # --------------------------------------------------------

    holidays = {
        "2024-01-26": "Republic Day",
        "2024-03-25": "Holi",
        "2024-08-15": "Independence Day",
        "2024-11-01": "Diwali",
        "2024-12-25": "Christmas",
        "2025-01-26": "Republic Day",
        "2025-03-14": "Holi",
        "2025-08-15": "Independence Day",
        "2025-10-20": "Diwali",
        "2025-12-25": "Christmas",
        "2026-01-26": "Republic Day",
        "2026-03-04": "Holi",
        "2026-08-15": "Independence Day",
        "2026-11-08": "Diwali",
        "2026-12-25": "Christmas",
    }

    calendar["holiday_name"] = (
        calendar["date"]
        .dt.strftime("%Y-%m-%d")
        .map(holidays)
    )

    calendar["is_holiday"] = calendar["holiday_name"].notna()

    # --------------------------------------------------------
    # Fiscal year
    # Indian financial year starts in April.
    # --------------------------------------------------------

    calendar["fiscal_year"] = np.where(
        calendar["date"].dt.month >= 4,
        calendar["date"].dt.year,
        calendar["date"].dt.year - 1
    )

    calendar["fiscal_year"] = (
        calendar["fiscal_year"].astype(str)
        + "-"
        + (calendar["fiscal_year"] + 1).astype(str)
    )

    calendar["fiscal_quarter"] = (
        ((calendar["date"].dt.month - 4) % 12) // 3 + 1
    )

    # --------------------------------------------------------
    # Business season
    # --------------------------------------------------------

    def get_season(month):
        if month in [3, 4, 5]:
            return "Summer"
        elif month in [6, 7, 8, 9]:
            return "Monsoon"
        elif month in [10, 11]:
            return "Festive"
        else:
            return "Winter"

    calendar["season"] = calendar["date"].dt.month.map(get_season)

    return calendar

# ============================================================
# STORE GENERATION
# ============================================================

def generate_stores():
    """Generate physical and digital store/channel records."""

    physical_stores = [
        ("Mumbai", "Maharashtra", "West"),
        ("Pune", "Maharashtra", "West"),
        ("Nashik", "Maharashtra", "West"),
        ("Nagpur", "Maharashtra", "Central"),
        ("Ahmedabad", "Gujarat", "West"),
        ("Surat", "Gujarat", "West"),
        ("Delhi", "Delhi", "North"),
        ("Jaipur", "Rajasthan", "North"),
        ("Lucknow", "Uttar Pradesh", "North"),
        ("Chandigarh", "Chandigarh", "North"),
        ("Kolkata", "West Bengal", "East"),
        ("Bhubaneswar", "Odisha", "East"),
        ("Patna", "Bihar", "East"),
        ("Guwahati", "Assam", "Northeast"),
        ("Bengaluru", "Karnataka", "South"),
        ("Mysuru", "Karnataka", "South"),
        ("Chennai", "Tamil Nadu", "South"),
        ("Hyderabad", "Telangana", "South"),
        ("Kochi", "Kerala", "South"),
        ("Coimbatore", "Tamil Nadu", "South"),
    ]

    rows = []

    # --------------------------------------------------------
    # 60 physical stores
    # --------------------------------------------------------

    for i in range(STORE_COUNT - 3):

        city, state, region = physical_stores[
            i % len(physical_stores)
        ]

        store_number = i + 1

        rows.append({
            "store_id": f"STR{store_number:03d}",
            "store_name": f"{city} Store {store_number}",
            "store_type": "Physical",
            "city": city,
            "state": state,
            "region": region,
            "opening_date": fake.date_between(
                start_date=pd.Timestamp("2021-01-01").date(),
                end_date=pd.Timestamp("2024-01-01").date()
            ),
            "store_size_sqft": int(
                rng.integers(1500, 12000)
            ),
            "status": rng.choice(
                ["Active", "Active", "Active", "Inactive"],
                p=[0.88, 0.06, 0.04, 0.02]
            )
        })

    # --------------------------------------------------------
    # Digital channels
    # --------------------------------------------------------

    digital_channels = [
        {
            "store_id": "STR061",
            "store_name": "Online Store",
            "city": "Mumbai",
            "state": "Maharashtra",
            "region": "West",
        },
        {
            "store_id": "STR062",
            "store_name": "Amazon",
            "city": "Mumbai",
            "state": "Maharashtra",
            "region": "West",
        },
        {
            "store_id": "STR063",
            "store_name": "Flipkart",
            "city": "Bengaluru",
            "state": "Karnataka",
            "region": "South",
        },
    ]

    for channel in digital_channels:

        rows.append({
            "store_id": channel["store_id"],
            "store_name": channel["store_name"],
            "store_type": (
                "Online"
                if channel["store_name"] == "Online Store"
                else "Marketplace"
            ),
            "city": channel["city"],
            "state": channel["state"],
            "region": channel["region"],
            "opening_date": pd.Timestamp("2021-01-01").date(),
            "store_size_sqft": 0,
            "status": "Active"
        })

    return pd.DataFrame(rows)

# ============================================================
# PRODUCT GENERATION
# ============================================================

def generate_products():
    """Generate the product dimension."""

    categories = {
        "Electronics": [
            "Smartphones",
            "Laptops",
            "Audio",
            "Cameras",
            "Accessories"
        ],
        "Home & Kitchen": [
            "Kitchen Appliances",
            "Cookware",
            "Home Decor",
            "Storage",
            "Cleaning"
        ],
        "Fashion": [
            "Men Clothing",
            "Women Clothing",
            "Footwear",
            "Bags",
            "Accessories"
        ],
        "Beauty & Personal Care": [
            "Skincare",
            "Haircare",
            "Makeup",
            "Fragrances",
            "Personal Care"
        ],
        "Sports & Fitness": [
            "Fitness Equipment",
            "Sportswear",
            "Outdoor",
            "Yoga",
            "Accessories"
        ],
        "Grocery": [
            "Staples",
            "Snacks",
            "Beverages",
            "Packaged Food",
            "Household"
        ],
        "Books": [
            "Fiction",
            "Non-Fiction",
            "Academic",
            "Children",
            "Self Help"
        ],
        "Toys & Games": [
            "Educational",
            "Board Games",
            "Action Figures",
            "Outdoor Games",
            "Puzzles"
        ],
        "Furniture": [
            "Tables",
            "Chairs",
            "Beds",
            "Storage Furniture",
            "Office Furniture"
        ],
        "Accessories": [
            "Mobile Accessories",
            "Travel Accessories",
            "Lifestyle",
            "Gadgets",
            "Utility"
        ],
    }

    brands = [
        "NovaTech",
        "UrbanNest",
        "StyleCraft",
        "PureGlow",
        "FitCore",
        "DailyChoice",
        "ReadMore",
        "PlayZone",
        "HomePro",
        "TrendLine",
        "Apex",
        "Vertex",
        "PrimeLife",
        "SmartBuy",
        "Essenza",
    ]

    supplier_regions = [
        "North",
        "South",
        "East",
        "West",
        "Central"
    ]

    rows = []

    category_names = list(categories.keys())

    for i in range(PRODUCT_COUNT):

        product_id = f"PRD{i + 1:06d}"

        category = rng.choice(category_names)

        subcategory = rng.choice(categories[category])

        # ----------------------------------------------------
        # Price ranges by category
        # ----------------------------------------------------

        price_ranges = {
            "Electronics": (5000, 120000),
            "Home & Kitchen": (300, 30000),
            "Fashion": (300, 15000),
            "Beauty & Personal Care": (200, 8000),
            "Sports & Fitness": (300, 25000),
            "Grocery": (50, 3000),
            "Books": (100, 2500),
            "Toys & Games": (200, 10000),
            "Furniture": (2000, 60000),
            "Accessories": (100, 12000),
        }

        min_price, max_price = price_ranges[category]

        base_price = round(
            rng.uniform(min_price, max_price),
            2
        )

        # ----------------------------------------------------
        # Cost produces realistic gross margins
        # ----------------------------------------------------

        margin_ranges = {
            "Electronics": (0.08, 0.22),
            "Home & Kitchen": (0.20, 0.40),
            "Fashion": (0.35, 0.60),
            "Beauty & Personal Care": (0.30, 0.55),
            "Sports & Fitness": (0.25, 0.45),
            "Grocery": (0.08, 0.20),
            "Books": (0.15, 0.30),
            "Toys & Games": (0.25, 0.45),
            "Furniture": (0.25, 0.45),
            "Accessories": (0.30, 0.55),
        }

        min_margin, max_margin = margin_ranges[category]

        margin = rng.uniform(
            min_margin,
            max_margin
        )

        unit_cost = round(
            base_price * (1 - margin),
            2
        )

        # ----------------------------------------------------
        # Launch date
        # ----------------------------------------------------

        launch_date = fake.date_between(
            start_date=pd.Timestamp("2022-01-01").date(),
            end_date=pd.Timestamp(END_DATE).date()
        )

        # ----------------------------------------------------
        # Product status
        # ----------------------------------------------------

        status = rng.choice(
            ["Active", "Discontinued", "Out of Stock"],
            p=[0.90, 0.06, 0.04]
        )

        # ----------------------------------------------------
        # Product rating
        # ----------------------------------------------------

        rating = round(
            np.clip(
                rng.normal(4.0, 0.5),
                2.5,
                5.0
            ),
            2
        )

        rating_count = int(
            rng.lognormal(
                mean=4.5,
                sigma=1.2
            )
        )

        rating_count = max(
            5,
            min(rating_count, 50000)
        )

        rows.append({
            "product_id": product_id,
            "product_name": (
                f"{brand if (brand := rng.choice(brands)) else 'Generic'} "
                f"{subcategory} {i + 1}"
            ),
            "category": category,
            "subcategory": subcategory,
            "brand": brand,
            "unit_cost": unit_cost,
            "base_price": base_price,
            "launch_date": launch_date,
            "product_status": status,
            "supplier_region": rng.choice(supplier_regions),
            "weight_kg": round(
                float(rng.lognormal(0, 0.7)),
                2
            ),
            "rating": rating,
            "rating_count": rating_count,
        })

    return pd.DataFrame(rows)


# ============================================================
# CUSTOMER GENERATION
# ============================================================

def generate_customers():
    """Generate customers with realistic demographic and
    behavioral segmentation."""

    regions = {
        "North": [
            ("Delhi", "Delhi"),
            ("Jaipur", "Rajasthan"),
            ("Lucknow", "Uttar Pradesh"),
            ("Chandigarh", "Chandigarh"),
        ],
        "South": [
            ("Bengaluru", "Karnataka"),
            ("Chennai", "Tamil Nadu"),
            ("Hyderabad", "Telangana"),
            ("Kochi", "Kerala"),
        ],
        "East": [
            ("Kolkata", "West Bengal"),
            ("Bhubaneswar", "Odisha"),
            ("Patna", "Bihar"),
        ],
        "West": [
            ("Mumbai", "Maharashtra"),
            ("Pune", "Maharashtra"),
            ("Nashik", "Maharashtra"),
            ("Ahmedabad", "Gujarat"),
            ("Surat", "Gujarat"),
        ],
        "Central": [
            ("Nagpur", "Maharashtra"),
            ("Bhopal", "Madhya Pradesh"),
            ("Indore", "Madhya Pradesh"),
        ],
        "Northeast": [
            ("Guwahati", "Assam"),
        ],
    }

    acquisition_channels = [
        "Organic",
        "Google Ads",
        "Meta Ads",
        "Email",
        "Referral",
        "Affiliate",
        "Direct",
        "Marketplace",
    ]

    devices = [
        "Mobile",
        "Desktop",
        "Tablet",
    ]

    segments = [
        "New",
        "Regular",
        "Loyal",
        "VIP",
        "At-Risk",
        "Dormant",
    ]

    rows = []

    # --------------------------------------------------------
    # Generate customers
    # --------------------------------------------------------

    for i in range(CUSTOMER_COUNT):

        customer_id = f"CUS{i + 1:06d}"

        region = rng.choice(
            list(regions.keys()),
            p=[
                0.18,  # North
                0.20,  # South
                0.12,  # East
                0.25,  # West
                0.15,  # Central
                0.10,  # Northeast
            ],
        )

        city, state = regions[region][
            rng.integers(len(regions[region]))
        ]

        # ----------------------------------------------------
        # Signup date
        # ----------------------------------------------------

        signup_date = fake.date_between(
            start_date=pd.Timestamp("2022-01-01").date(),
            end_date=pd.Timestamp(END_DATE).date(),
        )

        # ----------------------------------------------------
        # Customer segment
        #
        # Older customers are more likely to become Loyal/VIP.
        # Newer customers are more likely to be New.
        # ----------------------------------------------------

        customer_age_days = (
            pd.Timestamp(END_DATE)
            - pd.Timestamp(signup_date)
        ).days

        if customer_age_days < 180:
            segment = rng.choice(
                ["New", "Regular"],
                p=[0.75, 0.25],
            )

        elif customer_age_days < 365:
            segment = rng.choice(
                ["New", "Regular", "Loyal"],
                p=[0.20, 0.65, 0.15],
            )

        else:
            segment = rng.choice(
                segments,
                p=[
                    0.04,  # New
                    0.45,  # Regular
                    0.25,  # Loyal
                    0.08,  # VIP
                    0.10,  # At-Risk
                    0.08,  # Dormant
                ],
            )

        # ----------------------------------------------------
        # Demographics
        # ----------------------------------------------------

        gender = rng.choice(
            ["Male", "Female", "Other"],
            p=[0.49, 0.49, 0.02],
        )

        birth_year = int(
            np.clip(
                rng.normal(1992, 10),
                1955,
                2005,
            )
        )

        # ----------------------------------------------------
        # Acquisition channel
        # ----------------------------------------------------

        acquisition_channel = rng.choice(
            acquisition_channels,
            p=[
                0.18,  # Organic
                0.18,  # Google Ads
                0.16,  # Meta Ads
                0.10,  # Email
                0.12,  # Referral
                0.08,  # Affiliate
                0.10,  # Direct
                0.08,  # Marketplace
            ],
        )

        # ----------------------------------------------------
        # Device
        # ----------------------------------------------------

        preferred_device = rng.choice(
            devices,
            p=[
                0.68,  # Mobile
                0.27,  # Desktop
                0.05,  # Tablet
            ],
        )

        # ----------------------------------------------------
        # Customer status
        # ----------------------------------------------------

        if segment == "Dormant":
            status = "Inactive"

        elif segment == "At-Risk":
            status = rng.choice(
                ["Active", "Inactive"],
                p=[0.75, 0.25],
            )

        else:
            status = "Active"

        rows.append({
            "customer_id": customer_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"customer{i + 1:06d}@example.com",
            "gender": gender,
            "birth_year": birth_year,
            "signup_date": signup_date,
            "customer_segment": segment,
            "city": city,
            "state": state,
            "region": region,
            "postal_code": fake.postcode(),
            "acquisition_channel": acquisition_channel,
            "preferred_device": preferred_device,
            "customer_status": status,
        })

    return pd.DataFrame(rows)


# ============================================================
# MARKETING SPEND GENERATION
# ============================================================

def generate_marketing_spend():
    """Generate daily marketing campaign performance data."""

    channels = [
        "Google Ads",
        "Meta Ads",
        "Email",
        "Affiliate",
        "Influencer",
        "Search",
        "Display",
    ]

    regions = [
        "North",
        "South",
        "East",
        "West",
        "Central",
        "Northeast",
    ]

    # Campaign names by channel
    campaign_names = {
        "Google Ads": [
            "Search Performance",
            "Shopping Boost",
            "Brand Search",
            "High Intent Campaign",
        ],
        "Meta Ads": [
            "Summer Collection",
            "Festive Fashion",
            "Product Discovery",
            "Retargeting Campaign",
        ],
        "Email": [
            "Weekly Newsletter",
            "VIP Offers",
            "Cart Recovery",
            "Festival Offers",
        ],
        "Affiliate": [
            "Affiliate Partner Network",
            "Creator Affiliate",
            "Commerce Partners",
        ],
        "Influencer": [
            "Creator Campaign",
            "Festival Influencer Push",
            "Product Review Campaign",
        ],
        "Search": [
            "Organic Search Boost",
            "SEO Campaign",
            "Category Search",
        ],
        "Display": [
            "Retargeting Display",
            "Awareness Campaign",
            "Product Display",
        ],
    }

    # --------------------------------------------------------
    # Channel-specific average daily spend
    # --------------------------------------------------------

    spend_ranges = {
        "Google Ads": (15000, 80000),
        "Meta Ads": (10000, 70000),
        "Email": (3000, 20000),
        "Affiliate": (5000, 30000),
        "Influencer": (8000, 50000),
        "Search": (5000, 30000),
        "Display": (4000, 25000),
    }

    # Generate approximately 20k+ campaign records.
    dates = pd.date_range(
        start=START_DATE,
        end=END_DATE,
        freq="D"
    )

    rows = []

    for date in dates:

        # 20-25 campaign records per day
        campaigns_today = int(
            rng.integers(20, 25)
        )

        for _ in range(campaigns_today):

            channel = rng.choice(channels)

            region = rng.choice(
                regions,
                p=[
                    0.18,
                    0.20,
                    0.12,
                    0.25,
                    0.15,
                    0.10,
                ]
            )

            campaign_name = rng.choice(
                campaign_names[channel]
            )

            min_spend, max_spend = spend_ranges[channel]

            spend = rng.uniform(
                min_spend,
                max_spend
            )

            # ------------------------------------------------
            # Seasonal/event boost
            # ------------------------------------------------

            month = date.month

            seasonal_multiplier = 1.0

            if month in [10, 11]:
                seasonal_multiplier = 1.6

            elif month in [3, 4]:
                seasonal_multiplier = 1.2

            elif month in [6, 7, 8]:
                seasonal_multiplier = 1.1

            # Occasional marketing spikes
            if rng.random() < 0.025:
                seasonal_multiplier *= rng.uniform(
                    1.8,
                    3.0
                )

            spend *= seasonal_multiplier

            # ------------------------------------------------
            # Impressions
            # ------------------------------------------------

            # Higher spend generally creates more impressions,
            # but efficiency varies by channel.
            channel_efficiency = {
                "Google Ads": 0.95,
                "Meta Ads": 1.05,
                "Email": 1.35,
                "Affiliate": 1.10,
                "Influencer": 0.90,
                "Search": 1.20,
                "Display": 0.80,
            }

            impressions = int(
                spend
                * rng.uniform(0.8, 1.2)
                * channel_efficiency[channel]
                * 8
            )

            impressions = max(
                impressions,
                100
            )

            # ------------------------------------------------
            # Click-through rate
            # ------------------------------------------------

            ctr = rng.uniform(
                0.01,
                0.08
            )

            clicks = int(
                impressions * ctr
            )

            # ------------------------------------------------
            # Conversion rate
            # ------------------------------------------------

            conversion_rate = rng.uniform(
                0.015,
                0.10
            )

            conversions = int(
                clicks * conversion_rate
            )

            rows.append({
                "marketing_id": f"MKT{len(rows) + 1:08d}",
                "date": date.date(),
                "channel": channel,
                "campaign_name": campaign_name,
                "region": region,
                "spend": round(spend, 2),
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
            })

    return pd.DataFrame(rows)


# ============================================================
# ORDER GENERATION
# ============================================================

def generate_orders(customers, stores):
    """Generate orders using customer behavior, seasonality,
    regional patterns, and store/channel behavior."""

    # --------------------------------------------------------
    # Basic order IDs
    # --------------------------------------------------------

    order_ids = np.array([
        f"ORD{i:08d}"
        for i in range(1, ORDER_COUNT + 1)
    ])

    # --------------------------------------------------------
    # Customer selection
    #
    # Different segments have different purchase frequency.
    # --------------------------------------------------------

    segment_weights = {
        "New": 0.7,
        "Regular": 1.0,
        "Loyal": 1.8,
        "VIP": 3.0,
        "At-Risk": 0.45,
        "Dormant": 0.15,
    }

    customer_weights = (
        customers["customer_segment"]
        .map(segment_weights)
        .to_numpy()
    )

    customer_weights = (
        customer_weights / customer_weights.sum()
    )

    customer_indices = rng.choice(
        len(customers),
        size=ORDER_COUNT,
        p=customer_weights
    )

    selected_customers = customers.iloc[
        customer_indices
    ].reset_index(drop=True)

    # --------------------------------------------------------
    # Order dates
    # --------------------------------------------------------

    calendar = pd.date_range(
        start=START_DATE,
        end=END_DATE,
        freq="D"
    )

    # Create a business-seasonality weight for each date.
    date_weights = np.ones(len(calendar))

    for i, date in enumerate(calendar):

        # Weekend boost
        if date.dayofweek >= 5:
            date_weights[i] *= 1.15

        # Festive season
        if date.month in [10, 11]:
            date_weights[i] *= 1.65

        # New Year
        if date.month == 1:
            date_weights[i] *= 1.10

        # Summer sales
        if date.month in [3, 4, 5]:
            date_weights[i] *= 1.15

        # Monsoon campaigns
        if date.month in [6, 7, 8]:
            date_weights[i] *= 1.05

        # Occasional demand spike
        if rng.random() < 0.015:
            date_weights[i] *= rng.uniform(1.3, 2.0)

    date_weights /= date_weights.sum()

    order_dates = rng.choice(
        calendar,
        size=ORDER_COUNT,
        p=date_weights
    )

    order_dates = pd.to_datetime(order_dates)

    # --------------------------------------------------------
    # Store selection
    # --------------------------------------------------------

    store_weights = np.ones(len(stores))

    # Physical stores
    store_weights[
        stores["store_type"].eq("Physical").to_numpy()
    ] = 1.0

    # Online store gets higher order volume
    store_weights[
        stores["store_type"].eq("Online").to_numpy()
    ] = 3.5

    # Marketplaces also receive high volume
    store_weights[
        stores["store_type"].eq("Marketplace").to_numpy()
    ] = 2.5

    store_weights /= store_weights.sum()

    store_indices = rng.choice(
        len(stores),
        size=ORDER_COUNT,
        p=store_weights
    )

    selected_stores = stores.iloc[
        store_indices
    ].reset_index(drop=True)

    # --------------------------------------------------------
    # Order status
    # --------------------------------------------------------

    order_status = rng.choice(
        ["Completed", "Cancelled", "Pending"],
        size=ORDER_COUNT,
        p=[0.92, 0.06, 0.02]
    )

    # --------------------------------------------------------
    # Payment status
    # --------------------------------------------------------

    payment_status = np.where(
        order_status == "Cancelled",
        rng.choice(
            ["Failed", "Refunded"],
            size=ORDER_COUNT,
            p=[0.65, 0.35]
        ),
        np.where(
            order_status == "Pending",
            "Pending",
            "Paid"
        )
    )

    # --------------------------------------------------------
    # Shipping method
    # --------------------------------------------------------

    shipping_method = rng.choice(
        ["Standard", "Express", "Same Day"],
        size=ORDER_COUNT,
        p=[0.65, 0.25, 0.10]
    )

    # --------------------------------------------------------
    # Order timestamp
    # --------------------------------------------------------

    hours = rng.integers(
        8,
        23,
        size=ORDER_COUNT
    )

    minutes = rng.integers(
        0,
        60,
        size=ORDER_COUNT
    )

    seconds = rng.integers(
        0,
        60,
        size=ORDER_COUNT
    )

    order_timestamps = (
        order_dates
        + pd.to_timedelta(hours, unit="h")
        + pd.to_timedelta(minutes, unit="m")
        + pd.to_timedelta(seconds, unit="s")
    )

    # --------------------------------------------------------
    # Delivery date
    # --------------------------------------------------------

    delivery_days = np.select(
        [
            shipping_method == "Same Day",
            shipping_method == "Express",
            shipping_method == "Standard",
        ],
        [
            rng.integers(0, 2, size=ORDER_COUNT),
            rng.integers(1, 4, size=ORDER_COUNT),
            rng.integers(3, 9, size=ORDER_COUNT),
        ],
        default=5
    )

    delivery_dates = (
        order_dates
        + pd.to_timedelta(delivery_days, unit="D")
    )

    # Cancelled/pending orders generally don't have delivery.
    delivery_dates = pd.Series(delivery_dates)

    delivery_dates.loc[
        order_status != "Completed"
    ] = pd.NaT

    # --------------------------------------------------------
    # Discounts
    #
    # Festive periods have higher discounts.
    # --------------------------------------------------------

    discount_percent = rng.beta(
        2,
        10,
        size=ORDER_COUNT
    ) * 0.40

    festive_mask = order_dates.month.isin(
        [10, 11]
    )

    discount_percent[festive_mask] += rng.uniform(
        0.05,
        0.15,
        size=festive_mask.sum()
    )

    discount_percent = np.clip(
        discount_percent,
        0,
        0.50
    )

    # --------------------------------------------------------
    # Shipping fee
    # --------------------------------------------------------

    shipping_fee = np.select(
        [
            shipping_method == "Same Day",
            shipping_method == "Express",
            shipping_method == "Standard",
        ],
        [
            rng.uniform(120, 250, ORDER_COUNT),
            rng.uniform(70, 150, ORDER_COUNT),
            rng.uniform(30, 80, ORDER_COUNT),
        ],
        default=50
    )

    # Digital channels generally have lower shipping cost.
    digital_mask = selected_stores["store_type"].isin(
        ["Online", "Marketplace"]
    ).to_numpy()

    shipping_fee[digital_mask] *= rng.uniform(
        0.8,
        1.0,
        digital_mask.sum()
    )

    # --------------------------------------------------------
    # Temporary order values
    #
    # Actual order totals will be finalized after order_items
    # are generated.
    # --------------------------------------------------------

    order_total = np.zeros(ORDER_COUNT)

    # --------------------------------------------------------
    # Create dataframe
    # --------------------------------------------------------

    orders = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": selected_customers["customer_id"].to_numpy(),
        "store_id": selected_stores["store_id"].to_numpy(),
        "order_date": order_dates.date,
        "order_timestamp": order_timestamps,
        "order_status": order_status,
        "payment_status": payment_status,
        "shipping_method": shipping_method,
        "delivery_date": delivery_dates.dt.date,
        "discount_amount": np.zeros(ORDER_COUNT),
        "shipping_fee": np.round(shipping_fee, 2),
        "tax_amount": np.zeros(ORDER_COUNT),
        "order_total": order_total,
    })

    # Keep the discount percentage temporarily.
    # It will be used while generating order_items.
    orders["_discount_percent"] = discount_percent

    return orders


# ============================================================
# ORDER ITEM GENERATION
# ============================================================

def generate_order_items(orders, products):
    """
    Generate order-item rows.

    Grain:
        One row = one product line within an order.
    """

    # --------------------------------------------------------
    # Number of items per order
    # --------------------------------------------------------

    item_counts = rng.choice(
        [1, 2, 3, 4, 5],
        size=len(orders),
        p=[0.25, 0.35, 0.22, 0.12, 0.06],
    )

    total_items = int(item_counts.sum())

    print(f"Generating {total_items:,} order-item rows...")

    # --------------------------------------------------------
    # Repeat each order according to its item count
    # --------------------------------------------------------

    order_indices = np.repeat(
        np.arange(len(orders)),
        item_counts
    )

    selected_orders = orders.iloc[
        order_indices
    ].reset_index(drop=True)

    # --------------------------------------------------------
    # Generate product selection
    #
    # Products have different popularity levels.
    # This creates realistic product concentration.
    # --------------------------------------------------------

    product_weights = rng.lognormal(
        mean=0,
        sigma=1.0,
        size=len(products)
    )

    # Give a small group of products significantly higher
    # demand to create realistic "best sellers".
    popular_count = max(
        1,
        int(len(products) * 0.05)
    )

    popular_indices = rng.choice(
        len(products),
        size=popular_count,
        replace=False
    )

    product_weights[popular_indices] *= 4

    product_weights /= product_weights.sum()

    product_indices = rng.choice(
        len(products),
        size=total_items,
        p=product_weights
    )

    selected_products = products.iloc[
        product_indices
    ].reset_index(drop=True)

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    quantity = rng.choice(
        [1, 2, 3, 4],
        size=total_items,
        p=[0.65, 0.25, 0.08, 0.02]
    )

    # Grocery products tend to have higher quantities.
    grocery_mask = (
        selected_products["category"]
        .eq("Grocery")
        .to_numpy()
    )

    grocery_count = grocery_mask.sum()

    quantity[grocery_mask] = rng.choice(
        [1, 2, 3, 4, 5],
        size=grocery_count,
        p=[0.25, 0.30, 0.25, 0.15, 0.05]
    )

    # --------------------------------------------------------
    # Unit price
    #
    # Price is based on the product's base price.
    # Small variation represents actual selling price.
    # --------------------------------------------------------

    base_prices = (
        selected_products["base_price"]
        .to_numpy()
    )

    price_multiplier = rng.uniform(
        0.90,
        1.05,
        size=total_items
    )

    unit_price = (
        base_prices * price_multiplier
    )

    unit_price = np.round(
        unit_price,
        2
    )

    # --------------------------------------------------------
    # Discount
    #
    # Use the discount generated at order level.
    # --------------------------------------------------------

    order_discount = (
        selected_orders["_discount_percent"]
        .to_numpy()
    )

    # Small item-level variation
    discount_variation = rng.uniform(
        0.85,
        1.15,
        size=total_items
    )

    discount_percent = (
        order_discount * discount_variation
    )

    discount_percent = np.clip(
        discount_percent,
        0,
        0.50
    )

    # --------------------------------------------------------
    # Financial calculations
    # --------------------------------------------------------

    # Round discount percentage first because this is the
    # value that will be stored in the dataset.
    discount_percent = np.round(
        discount_percent,
        4
    )

    gross_revenue = (
        quantity * unit_price
    )

    discount_amount = (
        gross_revenue * discount_percent
    )

    net_revenue = (
        gross_revenue - discount_amount
    )

    unit_cost = (
        selected_products["unit_cost"]
        .to_numpy()
    )

    unit_cost = np.round(
        unit_cost,
        2
    )

    total_cost = (
        quantity * unit_cost
    )

    gross_profit = (
        net_revenue - total_cost
    )

    # --------------------------------------------------------
    # Order item IDs
    # --------------------------------------------------------

    order_item_ids = np.array([
        f"OIT{i:08d}"
        for i in range(1, total_items + 1)
    ])

    # --------------------------------------------------------
    # Build dataframe
    # --------------------------------------------------------

    order_items = pd.DataFrame({
        "order_item_id": order_item_ids,
        "order_id": selected_orders["order_id"].to_numpy(),
        "product_id": selected_products["product_id"].to_numpy(),
        "quantity": quantity,
        "unit_price": unit_price,
        "unit_cost": np.round(unit_cost, 2),
        "discount_percent": discount_percent,
        "discount_amount": np.round(
            discount_amount,
            2
        ),
        "gross_revenue": np.round(
            gross_revenue,
            2
        ),
        "net_revenue": np.round(
            net_revenue,
            2
        ),
        "total_cost": np.round(
            total_cost,
            2
        ),
        "gross_profit": np.round(
            gross_profit,
            2
        ),
    })

    return order_items


# ============================================================
# UPDATE ORDER FINANCIALS
# ============================================================

def update_order_financials(orders, order_items):
    """
    Calculate order-level financial values from order items.

    This ensures that orders.csv and order_items.csv
    remain financially consistent.
    """

    # --------------------------------------------------------
    # Aggregate item-level values by order
    # --------------------------------------------------------

    order_totals = (
        order_items
        .groupby("order_id")
        .agg(
            item_gross_revenue=("gross_revenue", "sum"),
            item_discount_amount=("discount_amount", "sum"),
            item_net_revenue=("net_revenue", "sum"),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Merge totals into orders
    # --------------------------------------------------------

    orders = orders.drop(
        columns=[
            "discount_amount",
            "tax_amount",
            "order_total"
        ],
        errors="ignore"
    )

    orders = orders.merge(
        order_totals,
        on="order_id",
        how="left"
    )

    # Orders without items should have zero values
    orders[
        [
            "item_gross_revenue",
            "item_discount_amount",
            "item_net_revenue"
        ]
    ] = orders[
        [
            "item_gross_revenue",
            "item_discount_amount",
            "item_net_revenue"
        ]
    ].fillna(0)

    # --------------------------------------------------------
    # Order-level financial fields
    # --------------------------------------------------------

    orders["discount_amount"] = (
        orders["item_discount_amount"]
    )

    # Tax is calculated on net revenue.
    # 18% is used as a simplified synthetic GST assumption.
    orders["tax_amount"] = (
        orders["item_net_revenue"] * 0.18
    )

    orders["tax_amount"] = orders[
        "tax_amount"
    ].round(2)

    # Order total includes:
    #
    # Net product revenue
    # + tax
    # + shipping fee
    #
    orders["order_total"] = (
        orders["item_net_revenue"]
        + orders["tax_amount"]
        + orders["shipping_fee"]
    )

    orders["order_total"] = orders[
        "order_total"
    ].round(2)

    # --------------------------------------------------------
    # Remove temporary columns
    # --------------------------------------------------------

    orders = orders.drop(
        columns=[
            "item_gross_revenue",
            "item_discount_amount",
            "item_net_revenue",
            "_discount_percent"
        ],
        errors="ignore"
    )

    return orders



# ============================================================
# PAYMENT GENERATION
# ============================================================

def generate_payments(orders):
    """
    Generate payment records based on the generated orders.

    Most orders have one successful payment.
    A small number have failed payment attempts or refunds.
    """

    print("Generating payments...")

    payments = []

    payment_methods = [
        "UPI",
        "Credit Card",
        "Debit Card",
        "Net Banking",
        "Cash on Delivery",
        "Wallet",
        "EMI",
    ]

    payment_method_probs = [
        0.35,
        0.22,
        0.15,
        0.08,
        0.10,
        0.07,
        0.03,
    ]

    payment_id_counter = 1

    # --------------------------------------------------------
    # Process each order
    # --------------------------------------------------------

    for _, order in orders.iterrows():

        order_id = order["order_id"]
        order_total = float(order["order_total"])
        order_date = order["order_date"]
        order_status = order["order_status"]

        # ----------------------------------------------------
        # Cancelled orders
        #
        # Some cancelled orders have a failed payment,
        # while others were successfully paid and refunded.
        # ----------------------------------------------------

        if order_status == "Cancelled":

            if rng.random() < 0.65:

                payment_status = "Failed"
                amount = 0.0
                refund_amount = 0.0

            else:

                payment_status = "Refunded"
                amount = order_total
                refund_amount = order_total

            payment_method = rng.choice(
                payment_methods,
                p=payment_method_probs
            )

            payments.append({
                "payment_id": f"PAY{payment_id_counter:08d}",
                "order_id": order_id,
                "payment_date": order_date,
                "payment_method": payment_method,
                "payment_status": payment_status,
                "amount": round(amount, 2),
                "transaction_reference": (
                    f"TXN{payment_id_counter:010d}"
                ),
                "refund_amount": round(
                    refund_amount,
                    2
                ),
            })

            payment_id_counter += 1

        # ----------------------------------------------------
        # Pending orders
        # ----------------------------------------------------

        elif order_status == "Pending":

            payment_method = rng.choice(
                payment_methods,
                p=payment_method_probs
            )

            payments.append({
                "payment_id": f"PAY{payment_id_counter:08d}",
                "order_id": order_id,
                "payment_date": order_date,
                "payment_method": payment_method,
                "payment_status": "Pending",
                "amount": 0.0,
                "transaction_reference": (
                    f"TXN{payment_id_counter:010d}"
                ),
                "refund_amount": 0.0,
            })

            payment_id_counter += 1

        # ----------------------------------------------------
        # Completed orders
        # ----------------------------------------------------

        else:

            payment_method = rng.choice(
                payment_methods,
                p=payment_method_probs
            )

            # Small percentage of orders experience a failed
            # payment attempt before succeeding.
            if rng.random() < 0.04:

                # Failed attempt
                payments.append({
                    "payment_id": f"PAY{payment_id_counter:08d}",
                    "order_id": order_id,
                    "payment_date": order_date,
                    "payment_method": payment_method,
                    "payment_status": "Failed",
                    "amount": 0.0,
                    "transaction_reference": (
                        f"TXN{payment_id_counter:010d}"
                    ),
                    "refund_amount": 0.0,
                })

                payment_id_counter += 1

                # Successful retry
                payment_date = (
                    pd.Timestamp(order_date)
                    + pd.Timedelta(
                        minutes=int(
                            rng.integers(5, 120)
                        )
                    )
                )

                payments.append({
                    "payment_id": f"PAY{payment_id_counter:08d}",
                    "order_id": order_id,
                    "payment_date": payment_date,
                    "payment_method": payment_method,
                    "payment_status": "Paid",
                    "amount": round(
                        order_total,
                        2
                    ),
                    "transaction_reference": (
                        f"TXN{payment_id_counter:010d}"
                    ),
                    "refund_amount": 0.0,
                })

                payment_id_counter += 1

            else:

                payments.append({
                    "payment_id": f"PAY{payment_id_counter:08d}",
                    "order_id": order_id,
                    "payment_date": order_date,
                    "payment_method": payment_method,
                    "payment_status": "Paid",
                    "amount": round(
                        order_total,
                        2
                    ),
                    "transaction_reference": (
                        f"TXN{payment_id_counter:010d}"
                    ),
                    "refund_amount": 0.0,
                })

                payment_id_counter += 1

    payments = pd.DataFrame(payments)

    return payments



# ============================================================
# RETURN GENERATION
# ============================================================

def generate_returns(order_items, products, orders):
    """
    Generate return records from actual order items.

    Return behavior varies by product category so that the
    dataset contains realistic business patterns.
    """

    print("Generating returns...")

    # --------------------------------------------------------
    # Merge product category into order items
    # --------------------------------------------------------

    item_data = order_items.merge(
        products[
            [
                "product_id",
                "category"
            ]
        ],
        on="product_id",
        how="left"
    )

    item_data = item_data.merge(
        orders[
            [
                "order_id",
                "order_date",
                "order_status"
            ]
        ],
        on="order_id",
        how="left"
    )

    # Only completed orders can generate normal returns
    item_data = item_data[
        item_data["order_status"] == "Completed"
    ].copy()

    # --------------------------------------------------------
    # Category-specific return probabilities
    # --------------------------------------------------------

    category_return_probability = {
        "Electronics": 0.085,
        "Home & Kitchen": 0.055,
        "Fashion": 0.125,
        "Beauty & Personal Care": 0.065,
        "Sports & Fitness": 0.060,
        "Grocery": 0.015,
        "Books": 0.025,
        "Toys & Games": 0.045,
        "Furniture": 0.080,
        "Accessories": 0.070,
    }

    # --------------------------------------------------------
    # Decide which order items are returned
    # --------------------------------------------------------

    probabilities = (
        item_data["category"]
        .map(category_return_probability)
        .fillna(0.05)
        .to_numpy()
    )

    return_mask = (
        rng.random(len(item_data))
        < probabilities
    )

    returned_items = item_data[
        return_mask
    ].copy()

    # --------------------------------------------------------
    # Return reason based on category
    # --------------------------------------------------------

    reasons = []

    for category in returned_items["category"]:

        if category == "Fashion":

            reason = rng.choice(
                [
                    "Size/Fit Issue",
                    "Changed Mind",
                    "Not as Expected",
                    "Poor Quality",
                    "Late Delivery",
                ],
                p=[
                    0.50,
                    0.15,
                    0.15,
                    0.12,
                    0.08,
                ],
            )

        elif category == "Electronics":

            reason = rng.choice(
                [
                    "Damaged",
                    "Poor Quality",
                    "Not as Expected",
                    "Wrong Product",
                    "Changed Mind",
                ],
                p=[
                    0.35,
                    0.30,
                    0.15,
                    0.12,
                    0.08,
                ],
            )

        elif category == "Furniture":

            reason = rng.choice(
                [
                    "Damaged",
                    "Poor Quality",
                    "Not as Expected",
                    "Late Delivery",
                    "Changed Mind",
                ],
                p=[
                    0.40,
                    0.25,
                    0.15,
                    0.12,
                    0.08,
                ],
            )

        elif category == "Grocery":

            reason = rng.choice(
                [
                    "Damaged",
                    "Poor Quality",
                    "Wrong Product",
                    "Not as Expected",
                ],
                p=[
                    0.30,
                    0.35,
                    0.20,
                    0.15,
                ],
            )

        else:

            reason = rng.choice(
                [
                    "Damaged",
                    "Wrong Product",
                    "Poor Quality",
                    "Changed Mind",
                    "Late Delivery",
                    "Not as Expected",
                    "Other",
                ],
                p=[
                    0.15,
                    0.12,
                    0.18,
                    0.20,
                    0.10,
                    0.18,
                    0.07,
                ],
            )

        reasons.append(reason)

    returned_items["return_reason"] = reasons

    # --------------------------------------------------------
    # Return quantity
    # --------------------------------------------------------

    return_quantities = []

    for quantity in returned_items["quantity"]:

        if quantity == 1:
            return_quantity = 1
        else:
            return_quantity = rng.integers(
                1,
                quantity + 1
            )

        return_quantities.append(
            return_quantity
        )

    returned_items["return_quantity"] = (
        return_quantities
    )

    # --------------------------------------------------------
    # Return date
    #
    # Returns happen after the original order date.
    # Most happen within 7–30 days.
    # --------------------------------------------------------

    return_offsets = rng.integers(
        3,
        31,
        size=len(returned_items)
    )

    returned_items["return_date"] = (
        pd.to_datetime(
            returned_items["order_date"]
        )
        + pd.to_timedelta(
            return_offsets,
            unit="D"
        )
    )

    # --------------------------------------------------------
    # Refund amount
    # --------------------------------------------------------

    refund_per_unit = (
        returned_items["net_revenue"]
        / returned_items["quantity"]
    )

    refund_amount = (
        refund_per_unit
        * returned_items["return_quantity"]
    )

    returned_items["refund_amount"] = (
        refund_amount.round(2)
    )

    # --------------------------------------------------------
    # Return status
    # --------------------------------------------------------

    returned_items["return_status"] = rng.choice(
        [
            "Approved",
            "Completed",
            "Rejected",
        ],
        size=len(returned_items),
        p=[
            0.25,
            0.70,
            0.05,
        ],
    )

    # --------------------------------------------------------
    # Product condition
    # --------------------------------------------------------

    returned_items["condition"] = rng.choice(
        [
            "Unused",
            "Opened",
            "Damaged",
            "Defective",
        ],
        size=len(returned_items),
        p=[
            0.30,
            0.35,
            0.20,
            0.15,
        ],
    )

    # --------------------------------------------------------
    # Return IDs
    # --------------------------------------------------------

    return_ids = np.array([
        f"RET{i:08d}"
        for i in range(
            1,
            len(returned_items) + 1
        )
    ])

    # --------------------------------------------------------
    # Build final dataframe
    # --------------------------------------------------------

    returns = pd.DataFrame({
        "return_id": return_ids,
        "order_id": returned_items["order_id"].to_numpy(),
        "order_item_id": returned_items[
            "order_item_id"
        ].to_numpy(),
        "return_date": returned_items[
            "return_date"
        ].dt.strftime("%Y-%m-%d"),
        "return_quantity": returned_items[
            "return_quantity"
        ].to_numpy(),
        "return_reason": returned_items[
            "return_reason"
        ].to_numpy(),
        "refund_amount": returned_items[
            "refund_amount"
        ].to_numpy(),
        "return_status": returned_items[
            "return_status"
        ].to_numpy(),
        "condition": returned_items[
            "condition"
        ].to_numpy(),
    })

    return returns



# ============================================================
# INVENTORY SNAPSHOT GENERATION
# ============================================================

def generate_inventory_snapshots(
    order_items,
    returns,
    orders,
    products,
    stores,
    calendar
):
    """
    Generate demand-driven inventory snapshots.

    Inventory is generated at a weekly product-store grain
    rather than daily for every product-store combination.

    This keeps the dataset practical while still allowing
    stock-level and stockout analysis.
    """

    print("Generating inventory snapshots...")

    # --------------------------------------------------------
    # Use weekly snapshots
    # --------------------------------------------------------

    snapshot_dates = pd.date_range(
        start=START_DATE,
        end=END_DATE,
        freq="7D"
    )

    # Use physical stores for inventory.
    # Digital channels do not maintain store-level inventory
    # in this synthetic model.
    physical_stores = stores[
        stores["store_type"] == "Physical"
    ].copy()

    # --------------------------------------------------------
    # Aggregate historical sales by week/product/store
    # --------------------------------------------------------

    sales = order_items.merge(
        orders[
            [
                "order_id",
                "store_id",
                "order_date",
                "order_status",
            ]
        ],
        on="order_id",
        how="left"
    )

    sales = sales[
        sales["order_status"] == "Completed"
    ].copy()

    sales["order_date"] = pd.to_datetime(
        sales["order_date"]
    )

    sales["week"] = (
        sales["order_date"]
        - pd.to_timedelta(
            sales["order_date"].dt.dayofweek,
            unit="D"
        )
    ).dt.normalize()

    weekly_sales = (
        sales
        .groupby(
            [
                "week",
                "store_id",
                "product_id"
            ]
        )["quantity"]
        .sum()
        .reset_index()
    )

    # --------------------------------------------------------
    # Aggregate returned quantities
    # --------------------------------------------------------

    weekly_returns = returns.copy()

    weekly_returns["return_date"] = pd.to_datetime(
        weekly_returns["return_date"]
    )

    weekly_returns["week"] = (
        weekly_returns["return_date"]
        - pd.to_timedelta(
            weekly_returns["return_date"].dt.dayofweek,
            unit="D"
        )
    ).dt.normalize()

    weekly_return_qty = (
        weekly_returns
        .groupby(
            [
                "week",
                "order_item_id"
            ]
        )["return_quantity"]
        .sum()
        .reset_index()
    )

    # --------------------------------------------------------
    # Product demand weights
    #
    # These determine how much inventory each product tends
    # to require.
    # --------------------------------------------------------

    product_demand = {}

    for _, product in products.iterrows():

        category = product["category"]

        category_multiplier = {
            "Electronics": 1.20,
            "Home & Kitchen": 1.00,
            "Fashion": 1.30,
            "Beauty & Personal Care": 1.10,
            "Sports & Fitness": 0.90,
            "Grocery": 1.50,
            "Books": 0.60,
            "Toys & Games": 0.80,
            "Furniture": 0.45,
            "Accessories": 1.00,
        }.get(category, 1.0)

        product_demand[
            product["product_id"]
        ] = category_multiplier

    # --------------------------------------------------------
    # Generate snapshots
    # --------------------------------------------------------

    records = []

    snapshot_id = 1

    # Initial stock state for each store/product
    stock_state = {}

    for store_id in physical_stores["store_id"]:

        for product_id in products["product_id"]:

            product = products[
                products["product_id"] == product_id
            ].iloc[0]

            base_stock = int(
                rng.integers(20, 100)
                * product_demand[product_id]
            )

            stock_state[
                (store_id, product_id)
            ] = max(
                base_stock,
                5
            )

    # --------------------------------------------------------
    # Iterate through weeks
    # --------------------------------------------------------

    for snapshot_date in snapshot_dates:

        # Sales for current week
        current_sales = weekly_sales[
            weekly_sales["week"]
            == snapshot_date
        ]

        sales_lookup = {
            (
                row["store_id"],
                row["product_id"]
            ): int(row["quantity"])
            for _, row in current_sales.iterrows()
        }

        # ----------------------------------------------------
        # Generate each physical store/product snapshot
        # ----------------------------------------------------

        for store_id in physical_stores["store_id"]:

            for product_id in products["product_id"]:

                key = (
                    store_id,
                    product_id
                )

                opening_stock = stock_state[key]

                units_sold = sales_lookup.get(
                    key,
                    0
                )

                # ------------------------------------------------
                # Occasional demand spike
                # ------------------------------------------------

                if rng.random() < 0.03:

                    units_sold = int(
                        units_sold
                        * rng.uniform(
                            1.5,
                            2.5
                        )
                    )

                # ------------------------------------------------
                # Reorder level
                # ------------------------------------------------

                reorder_level = max(
                    int(
                        10
                        + units_sold * 1.5
                    ),
                    10
                )

                # ------------------------------------------------
                # Stockout scenario
                #
                # Small probability of delayed replenishment.
                # ------------------------------------------------

                stockout_event = (
                    opening_stock > 0
                    and units_sold > opening_stock
                    and rng.random() < 0.65
                )

                if stockout_event:

                    actual_units_sold = opening_stock

                    units_received = 0

                    closing_stock = 0

                    stockout_flag = 1

                else:

                    actual_units_sold = min(
                        units_sold,
                        opening_stock
                    )

                    # ------------------------------------------------
                    # Replenishment
                    # ------------------------------------------------

                    if (
                        opening_stock
                        <= reorder_level
                    ):

                        units_received = int(
                            rng.integers(
                                20,
                                100
                            )
                        )

                    else:

                        units_received = 0

                    closing_stock = (
                        opening_stock
                        + units_received
                        - actual_units_sold
                    )

                    stockout_flag = int(
                        closing_stock == 0
                        and actual_units_sold > 0
                    )

                # ------------------------------------------------
                # Returned units
                #
                # Keep inventory equation consistent.
                # ------------------------------------------------

                units_returned = 0

                # Returns are intentionally kept small at
                # inventory level to avoid double counting.
                if rng.random() < 0.08:

                    units_returned = int(
                        rng.integers(
                            0,
                            3
                        )
                    )

                    units_returned = min(
                        units_returned,
                        actual_units_sold
                    )

                    closing_stock += units_returned

                # ------------------------------------------------
                # Final inventory equation
                # ------------------------------------------------

                closing_stock = max(
                    int(
                        opening_stock
                        + units_received
                        - actual_units_sold
                        + units_returned
                    ),
                    0
                )

                records.append({
                    "snapshot_id": (
                        f"INV{snapshot_id:09d}"
                    ),
                    "snapshot_date": (
                        snapshot_date.strftime(
                            "%Y-%m-%d"
                        )
                    ),
                    "store_id": store_id,
                    "product_id": product_id,
                    "opening_stock": int(
                        opening_stock
                    ),
                    "units_received": int(
                        units_received
                    ),
                    "units_sold": int(
                        actual_units_sold
                    ),
                    "units_returned": int(
                        units_returned
                    ),
                    "closing_stock": int(
                        closing_stock
                    ),
                    "reorder_level": int(
                        reorder_level
                    ),
                    "stockout_flag": int(
                        stockout_flag
                    ),
                })

                stock_state[key] = closing_stock

                snapshot_id += 1

    inventory = pd.DataFrame(records)

    return inventory



# ============================================================
# TEST CONFIGURATION
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Agentic BI Analyst - Synthetic Data Generator")
    print("=" * 60)

    print(f"Seed: {SEED}")
    print(f"Date range: {START_DATE} → {END_DATE}")
    print(f"Customers: {CUSTOMER_COUNT:,}")
    print(f"Products: {PRODUCT_COUNT:,}")
    print(f"Stores: {STORE_COUNT:,}")
    print(f"Orders: {ORDER_COUNT:,}")
    print(f"Output directory: {OUTPUT_DIR}")

    # --------------------------------------------------------
    # Calendar
    # --------------------------------------------------------

    print("\nGenerating calendar...")

    calendar = generate_calendar()

    calendar.to_csv(
        OUTPUT_DIR / "calendar.csv",
        index=False
    )

    print(f"Calendar rows: {len(calendar):,}")
    print("calendar.csv created successfully.")

    # --------------------------------------------------------
    # Stores
    # --------------------------------------------------------

    print("\nGenerating stores...")

    stores = generate_stores()

    stores.to_csv(
        OUTPUT_DIR / "stores.csv",
        index=False
    )

    print(f"Store rows: {len(stores):,}")
    print("stores.csv created successfully.")


    # --------------------------------------------------------
    # Products
    # --------------------------------------------------------

    print("\nGenerating products...")

    products = generate_products()

    products.to_csv(
        OUTPUT_DIR / "products.csv",
        index=False
    )

    print(f"Product rows: {len(products):,}")
    print("products.csv created successfully.")


    # --------------------------------------------------------
    # Customers
    # --------------------------------------------------------

    print("\nGenerating customers...")

    customers = generate_customers()

    customers.to_csv(
        OUTPUT_DIR / "customers.csv",
        index=False
    )

    print(f"Customer rows: {len(customers):,}")
    print("customers.csv created successfully.")


    # --------------------------------------------------------
    # Marketing Spend
    # --------------------------------------------------------

    print("\nGenerating marketing spend...")

    marketing_spend = generate_marketing_spend()

    marketing_spend.to_csv(
        OUTPUT_DIR / "marketing_spend.csv",
        index=False
    )

    print(
        f"Marketing rows: {len(marketing_spend):,}"
    )

    print(
        "marketing_spend.csv created successfully."
    )


    # --------------------------------------------------------
    # Orders
    # --------------------------------------------------------

    print("\nGenerating orders...")

    orders = generate_orders(
        customers,
        stores
    )

    orders.to_csv(
        OUTPUT_DIR / "orders.csv",
        index=False
    )

    print(f"Order rows: {len(orders):,}")
    print("orders.csv created successfully.")


    # --------------------------------------------------------
    # Order Items
    # --------------------------------------------------------

    print("\nGenerating order items...")

    order_items = generate_order_items(
        orders,
        products
    )

    order_items.to_csv(
        OUTPUT_DIR / "order_items.csv",
        index=False
    )

    print(
        f"Order item rows: {len(order_items):,}"
    )

    print(
        "order_items.csv created successfully."
    )

    # --------------------------------------------------------
    # Update Order Financials
    # --------------------------------------------------------

    print("\nUpdating order financials...")

    orders = update_order_financials(
        orders,
        order_items
    )

    orders.to_csv(
        OUTPUT_DIR / "orders.csv",
        index=False
    )

    print(
        "orders.csv updated successfully."
    )

    # --------------------------------------------------------
    # Payments
    # --------------------------------------------------------

    print("\nGenerating payments...")

    payments = generate_payments(
        orders
    )

    payments.to_csv(
        OUTPUT_DIR / "payments.csv",
        index=False
    )

    print(
        f"Payment rows: {len(payments):,}"
    )

    print(
        "payments.csv created successfully."
    )

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    print("\nGenerating returns...")

    returns = generate_returns(
        order_items,
        products,
        orders
    )

    returns.to_csv(
        OUTPUT_DIR / "returns.csv",
        index=False
    )

    print(
        f"Return rows: {len(returns):,}"
    )

    print(
        "returns.csv created successfully."
    )

    # --------------------------------------------------------
    # Inventory Snapshots
    # --------------------------------------------------------

    print("\nGenerating inventory snapshots...")

    inventory = generate_inventory_snapshots(
        order_items,
        returns,
        orders,
        products,
        stores,
        calendar
    )

    inventory.to_csv(
        OUTPUT_DIR / "inventory_snapshots.csv",
        index=False
    )

    print(
        f"Inventory rows: {len(inventory):,}"
    )

    print(
        "inventory_snapshots.csv created successfully."
    )






