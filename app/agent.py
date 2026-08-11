# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

MODEL = "gemini-3.6-flash"


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends session history to Vertex AI Memory Bank for long-term fact & preference extraction."""
    await callback_context.add_session_to_memory()
    return None


def search_anniversary_packages(destination_style: str, milestone_years: int = 25, max_budget: float = 6000.0) -> str:
    """Searches curated romantic travel packages tailored to milestone anniversaries and budget limits.

    Args:
        destination_style: The desired style of trip, e.g. "beach", "island", "europe", "mountains", "luxury".
        milestone_years: The anniversary milestone being celebrated (e.g., 25 for Silver Anniversary).
        max_budget: The maximum budget for the trip in USD.

    Returns:
        A string describing matching curated packages with pricing and romantic highlights.
    """
    style = destination_style.lower()
    milestone_tag = f"{milestone_years}th Anniversary" if milestone_years else "Anniversary"
    
    if "beach" in style or "island" in style:
        return (
            f"--- [Package Option A: Maui Silver Luxury Beach Resort] ---\n"
            f"• Tailored for: {milestone_tag}\n"
            f"• Location: Wailea, Maui, Hawaii\n"
            f"• Duration: 5 Days / 4 Nights\n"
            f"• Estimated Cost: $4,800 total ($1,200 flights + $2,800 5-star beachfront resort + $800 dining & activities)\n"
            f"• Highlights: Private beachfront sunset dinner, complimentary silver-trimmed anniversary cake, private cabana day.\n\n"
            f"--- [Package Option B: Amalfi Coast Cliffside Romance] ---\n"
            f"• Tailored for: {milestone_tag}\n"
            f"• Location: Positano, Italy\n"
            f"• Duration: 6 Days / 5 Nights\n"
            f"• Estimated Cost: $5,600 total ($1,600 flights + $3,000 cliffside suite + $1,000 fine dining)\n"
            f"• Highlights: Private boat tour along Capri, Michelin-star anniversary dinner, silver vow renewal setup overlooking the sea."
        )
    elif "europe" in style or "culture" in style:
        return (
            f"--- [Package Option: Paris & Loire Valley Chateau Romance] ---\n"
            f"• Tailored for: {milestone_tag}\n"
            f"• Location: Paris & Amboise, France\n"
            f"• Duration: 6 Days / 5 Nights\n"
            f"• Estimated Cost: $5,400 total ($1,400 flights + $2,800 boutique hotels + $1,200 dining & wine tours)\n"
            f"• Highlights: Private Seine River sunset dinner cruise, private wine tasting in a historic chateau cellar."
        )
    else:
        return (
            f"--- [Package Option: St. Lucia Piton Luxury Sanctuary] ---\n"
            f"• Tailored for: {milestone_tag}\n"
            f"• Location: Soufrière, St. Lucia\n"
            f"• Duration: 5 Days / 4 Nights\n"
            f"• Estimated Cost: $5,200 total ($1,400 flights + $2,800 open-air villa + $1,000 activities)\n"
            f"• Highlights: Private plunge pool overlooking the Pitons, silver anniversary spa treatment for two."
        )


def calculate_itemized_budget(flight_estimate: float, nightly_resort_rate: float, nights: int, dining_daily_budget: float, milestone_activity_cost: float, max_budget: float) -> str:
    """Calculates itemized total budget, estimated taxes/fees, and compares against maximum target budget.

    Args:
        flight_estimate: Total roundtrip flight estimate for two people.
        nightly_resort_rate: Nightly resort room rate.
        nights: Number of nights staying.
        dining_daily_budget: Estimated daily food & beverage budget for two.
        milestone_activity_cost: Total cost for special milestone activities (vow renewal, private dinner, spa).
        max_budget: The couple's total target budget limit.

    Returns:
        An itemized breakdown string showing total cost, variance from budget, and feasibility.
    """
    resort_total = nightly_resort_rate * nights
    dining_total = dining_daily_budget * (nights + 1)
    subtotal = flight_estimate + resort_total + dining_total + milestone_activity_cost
    taxes_fees = subtotal * 0.12  # estimated 12% taxes/fees
    total = subtotal + taxes_fees
    remaining = max_budget - total

    status = "WITHIN BUDGET ✅" if remaining >= 0 else "EXCEEDS BUDGET ⚠️"
    
    return (
        f"--- Itemized Budget Breakdown ---\n"
        f"• Roundtrip Flights (2 people): ${flight_estimate:,.2f}\n"
        f"• Resort Stay ({nights} nights @ ${nightly_resort_rate:,.2f}/night): ${resort_total:,.2f}\n"
        f"• Dining & Fine Food ({nights+1} days @ ${dining_daily_budget:,.2f}/day): ${dining_total:,.2f}\n"
        f"• Milestone Celebrations/Activities: ${milestone_activity_cost:,.2f}\n"
        f"• Estimated Taxes & Resort Fees (12%): ${taxes_fees:,.2f}\n"
        f"----------------------------------------\n"
        f"• TOTAL ESTIMATED COST: ${total:,.2f}\n"
        f"• Target Budget: ${max_budget:,.2f}\n"
        f"• Budget Variance: ${remaining:,.2f} ({status})"
    )


def get_special_milestone_experiences(milestone_years: int = 25) -> str:
    """Provides special celebration ideas and traditions for specific relationship milestones.

    Args:
        milestone_years: The anniversary milestone being celebrated.

    Returns:
        A string with special celebration ideas and gift traditions.
    """
    if milestone_years == 25:
        return (
            "--- 25th 'Silver' Anniversary Celebration Ideas ---\n"
            "• Traditional Symbol: Sterling Silver (represents durability, radiance, and lasting value).\n"
            "• Special Experiences:\n"
            "  1. Private Beach Vow Renewal with a silver ring/band exchange.\n"
            "  2. Sunset Candlelight Dinner featuring a personalized silver-embossed menu and silver champagne toast.\n"
            "  3. Custom Couples Spa Journey using silver-infused botanical oils.\n"
            "  4. Keepsake Experience: Commemorative silver photo book or custom engraved silver jewelry during the trip."
        )
    elif milestone_years == 50:
        return "--- 50th 'Golden' Anniversary Celebration Ideas ---\n• Traditional Symbol: Gold.\n• Highlights: Golden Jubilee gala dinner, family reunion resort booking, private helicopter tour."
    elif milestone_years == 10:
        return "--- 10th 'Tin/Aluminum' Anniversary Celebration Ideas ---\n• Traditional Symbol: Tin or Aluminum.\n• Highlights: Adventure getaway, private wine tasting, weekend luxury escape."
    else:
        return f"--- {milestone_years}th Anniversary Ideas ---\n• Highlights: Private romantic dinner, sunset yacht cruise, luxury couples massage."


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are an expert, warm, and attentive Milestone Anniversary Travel Concierge. "
        "Your mission is to help couples plan memorable, romantic, and stress-free anniversary trips "
        "tailored to their relationship stage, desires, and budget constraints.\n\n"
        "You automatically recall the user's stated preferences, anniversary dates, dietary needs, budget limits, "
        "and favorite destinations across conversations using your Memory Bank.\n\n"
        "Special Focus:\n"
        "• Pay special attention to 25th 'Silver' Anniversaries, emphasizing milestone touches like vow renewals, "
        "sunset dining, and silver traditions.\n"
        "• Always inquire about or take into account the couple's target budget, preferred travel style (beach, culture, mountains), and duration.\n"
        "• Use your tools to search curated packages, calculate itemized budget breakdowns, and suggest milestone celebration experiences."
    ),
    tools=[
        PreloadMemoryTool(),
        search_anniversary_packages,
        calculate_itemized_budget,
        get_special_milestone_experiences,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
