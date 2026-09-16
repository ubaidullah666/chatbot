"""
Domain Configuration for ApexDrive - Car Rental Assistant.
Contains fleet catalog, pricing rules, insurance tiers, policies,
and stage definitions to guide prompt orchestration.
"""

from typing import Dict, List, Any

DOMAIN_METADATA = {
    "name": "ApexDrive Car Rental",
    "assistant_name": "ApexDrive AI",
    "tagline": "Your Intelligent Fleet & Booking Concierge",
    "currency": "USD",
    "currency_symbol": "$",
}

FLEET_CATALOG: Dict[str, Dict[str, Any]] = {
    "Economy": {
        "models": ["Toyota Corolla", "Hyundai Elantra"],
        "daily_rate": 45,
        "transmission": "Automatic",
        "seats": 5,
        "luggage": "2 Large Bags",
        "mileage": "Unlimited",
        "best_for": "Budget city driving, daily commutes, solo travelers or couples."
    },
    "SUV": {
        "models": ["Toyota RAV4", "Ford Explorer"],
        "daily_rate": 75,
        "transmission": "Automatic (AWD)",
        "seats": 5,
        "luggage": "4 Large Bags",
        "mileage": "Unlimited",
        "best_for": "Family road trips, mountain getaways, all-weather comfort."
    },
    "Electric": {
        "models": ["Tesla Model 3", "Polestar 2"],
        "daily_rate": 85,
        "transmission": "Single-Speed Automatic",
        "seats": 5,
        "luggage": "3 Bags (Frunk + Trunk)",
        "mileage": "Unlimited + Free Supercharging for first 200 miles",
        "best_for": "Eco-friendly cruising, cutting-edge tech, zero fuel cost."
    },
    "Luxury": {
        "models": ["BMW 4 Series Gran Coupe", "Mercedes-Benz C-Class"],
        "daily_rate": 135,
        "transmission": "Sport Automatic",
        "seats": 5,
        "luggage": "3 Large Bags",
        "mileage": "Unlimited",
        "best_for": "Executive business travel, special occasions, premium comfort."
    }
}

INSURANCE_TIERS: Dict[str, Dict[str, Any]] = {
    "Standard CDW": {
        "daily_cost": 15,
        "excess_deductible": 500,
        "covers": "Collision Damage Waiver with $500 excess liability. Third-party liability included."
    },
    "Zero Excess Premium": {
        "daily_cost": 28,
        "excess_deductible": 0,
        "covers": "Complete peace of mind. $0 damage deductible, tyre & windscreen protection, theft waiver."
    },
    "Roadside Plus": {
        "daily_cost": 7,
        "excess_deductible": 0,
        "covers": "24/7 towing, battery jumpstarts, lockout service, and flat tyre assistance."
    }
}

OPTIONAL_ADDONS: Dict[str, Dict[str, Any]] = {
    "Child Safety Seat": {"daily_rate": 10, "unit": "per day"},
    "Additional Driver": {"daily_rate": 12, "unit": "per day"},
    "GPS Navigation Unit": {"daily_rate": 8, "unit": "per day"},
}

RENTAL_POLICIES: List[str] = [
    "Age Requirement: Primary driver must be at least 21 years old. Drivers aged 21-24 are subject to a Young Driver Surcharge of $20/day.",
    "Driver's License: Must hold a valid, unexpired driver's license for a minimum of 1 full year. International renters require an International Driving Permit (IDP) alongside their national license.",
    "Security Deposit: A refundable credit card pre-authorization of $200 is held at pickup and released upon return inspection.",
    "Cancellation Policy: 100% free cancellation up to 24 hours prior to scheduled pickup time.",
    "Fuel Policy: Full-to-Full. Vehicles are provided with a full tank/battery and must be returned with a full tank/battery to avoid refueling surcharges.",
    "Payment Methods: Major Credit Cards (Visa, Mastercard, Amex) accepted. Debit cards accepted only with proof of return flight tickets."
]

CONVERSATION_STAGES = {
    "GREETING": {
        "objective": "Welcome the guest warmly, state identity as ApexDrive AI, and inquire about their trip dates, preferred pickup location (Airport or Downtown), or desired vehicle category.",
        "sample_prompts": ["Welcome to ApexDrive!", "How can I help you with your vehicle rental today?"]
    },
    "INFORMATION_GATHERING": {
        "objective": "Elicit essential booking parameters: pickup & drop-off dates/duration, vehicle class (Economy, SUV, Electric, Luxury), driver age (to verify young driver surcharge), and insurance preference.",
        "sample_prompts": ["What dates do you need the car for?", "Which vehicle category fits your trip best?"]
    },
    "QUOTATION_CONFIRMATION": {
        "objective": "Present an itemized price breakdown (Daily Base Rate x Days + Insurance + Surcharges + Deposit notice). Check if all details match the customer's intent, and request explicit confirmation to finalize.",
        "sample_prompts": ["Here is your complete quote breakdown...", "Would you like me to reserve this vehicle for you?"]
    },
    "CLOSING": {
        "objective": "Generate a unique reservation reference code (e.g. APX-91428), summarize pickup location instructions, remind the guest to bring their physical driver's license and credit card for the $200 deposit, and offer parting assistance.",
        "sample_prompts": ["Your booking is confirmed! Your reference code is APX-...", "Safe travels with ApexDrive!"]
    },
    "DEFLECTION_HANDLING": {
        "objective": "Politely decline queries outside car rental, fleet specifications, pricing, and company policies (e.g., coding, general knowledge, sports, unrelated travel advice). Gently steer the conversation back to rental assistance.",
        "rule": "Always apologize politely, state clearly that you are exclusively trained as ApexDrive's rental concierge, and invite the user back to car rental options."
    }
}
