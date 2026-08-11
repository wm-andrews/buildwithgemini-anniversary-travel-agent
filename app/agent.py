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
import json
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback

MODEL = "gemini-3.6-flash"

# HARDCODED Project ID, Storage Bucket, and Agent Engine Resource
PROJECT_ID = "qwiklabs-gcp-03-3e728b1ac810"
COLLECTION_NAME = "anniversary_itineraries"
BUCKET_NAME = "anniversary-travel-assets-qwiklabs-gcp-03-3e728b1ac810"
AGENT_ENGINE_RESOURCE_NAME = (
    "projects/106477491386/locations/us-east1/reasoningEngines/444536949156347904"
)

# Build A2UI v0.8 System Prompt using A2uiSchemaManager & BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_system_prompt = schema_manager.generate_system_prompt(
    role_description=(
        "An expert, warm, and attentive Milestone Anniversary Travel Concierge helping couples plan "
        "memorable, romantic, and stress-free anniversary trips tailored to their relationship stage, desires, and budget."
    ),
    workflow_description=(
        "Analyze the user's request and return structured A2UI visual cards when appropriate, or call tools when real data or actions are required.\n"
        "Special Agent Capabilities & Rules:\n"
        "• Memory Bank: Automatically recall stated preferences, anniversary dates, dietary needs, budget limits across sessions.\n"
        "• Code Execution Sandbox: You have access to AgentEngineSandboxCodeExecutor to safely run Python scripts for complex mathematical calculations, budget modeling, date/milestone math, and data analysis.\n"
        "• Image Generation: Generate custom romantic anniversary concept art using generate_anniversary_concept_art.\n"
        "• Live Weather & Sunset: Check real-time destination weather, high/low temps, precipitation, and local sunset times using get_destination_weather.\n"
        "• Firestore Backend: List, retrieve, and save custom anniversary itineraries directly to Cloud Firestore collection 'anniversary_itineraries'.\n"
        "• Special Focus: Pay special attention to 25th 'Silver' Anniversaries, emphasizing silver traditions, vow renewals, and private sunset dining."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use Table or Heading (unsupported), "
        "or Buttons, actions, or forms (they do nothing in adk web). "
        "You may include one Image component, but only when you have a public https URL for the image (for example "
        "the URL returned by generate_anniversary_concept_art after uploading to Cloud Storage). Set the Image url to "
        'that exact https link, for example {"Image": {"url": {"literalString": "https://..."}}}. Never point an Image '
        "at a bare filename, an artifact name, or a non-http(s) path. If you do not have a public URL, add a short Text "
        "line noting the image instead. No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings "
        "and emphasis. Output ONLY the raw A2UI JSON array — no prose, and never wrap it in <a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends session history to Vertex AI Memory Bank for long-term fact & preference extraction."""
    await callback_context.add_session_to_memory()
    return None


def generate_anniversary_concept_art(prompt_description: str, tool_context: ToolContext) -> str:
    """Generates romantic anniversary trip concept art (e.g. sunset beachfront dinners, vow renewals, chateau views)
    using gemini-3.1-flash-lite-image in the global region. Saves the image to Playground Artifacts and uploads it
    to public Cloud Storage.

    Args:
        prompt_description: Detailed prompt describing the romantic scene (e.g. "A romantic 25th Silver Anniversary beachfront sunset dinner in Maui with silver candlelight and ocean views").

    Returns:
        A string containing the public Cloud Storage HTTPS URL of the generated image.
    """
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt_description,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return "Unable to generate image bytes for the requested prompt."

        artifact_filename = f"concept_art_{int(time.time())}.jpg"
        if tool_context:
            tool_context.save_artifact(
                filename=artifact_filename,
                artifact=types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            )

        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(artifact_filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{artifact_filename}"
        return (
            f"🎨 Successfully generated romantic anniversary concept art!\n"
            f"• Saved to Playground Artifacts: {artifact_filename}\n"
            f"• Public Image HTTPS URL: {public_url}"
        )
    except Exception as e:
        return f"Error generating concept art image: {str(e)}"


def generate_anniversary_video_teaser(prompt_description: str, tool_context: ToolContext) -> str:
    """Generates a short romantic video teaser for an anniversary travel destination or celebration
    using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video artifact to Playground Artifacts and uploads the video bytes to public Cloud Storage.

    Args:
        prompt_description: Detailed description of the video scene (e.g. "A romantic short video teaser of a sunset oceanfront dinner in Maui Hawaii").

    Returns:
        A string containing the public Cloud Storage HTTPS URL of the generated video.
    """
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=prompt_description,
            config=types.GenerateContentConfig(
                response_modalities=["VIDEO"],
            ),
        )

        video_bytes = None
        mime_type = "video/mp4"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    video_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not video_bytes:
            return "Unable to generate video bytes for the requested prompt."

        ext = "mp4"
        if "webm" in mime_type:
            ext = "webm"
        artifact_filename = f"video_teaser_{int(time.time())}.{ext}"

        if tool_context:
            tool_context.save_artifact(
                filename=artifact_filename,
                artifact=types.Part.from_bytes(data=video_bytes, mime_type=mime_type),
            )

        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(artifact_filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{artifact_filename}"
        return (
            f"🎬 Successfully generated romantic anniversary video teaser!\n"
            f"• Saved to Playground Artifacts: {artifact_filename}\n"
            f"• Public Video HTTPS URL: {public_url}"
        )
    except Exception as e:
        return f"Error generating anniversary video teaser: {str(e)}"


def get_destination_weather(destination_name: str) -> str:
    """Fetches real-time weather, temperatures, precipitation, and exact sunset times for any travel destination using the Open-Meteo API.

    Args:
        destination_name: Name of the destination city, island, or region (e.g. 'Maui', 'Positano', 'Paris', 'St. Lucia').

    Returns:
        A formatted string with live weather conditions, sunset timing, and romantic dining recommendations.
    """
    try:
        encoded_name = urllib.parse.quote(destination_name)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_name}&count=1"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "ADK-Agent/1.0"})
        with urllib.request.urlopen(req) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))

        results = geo_data.get("results")
        if not results:
            return f"Could not find geographic coordinates for '{destination_name}'. Please verify the destination name."

        location = results[0]
        lat, lon = location["latitude"], location["longitude"]
        loc_name = location.get("name", destination_name)
        country = location.get("country", "")

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            "&daily=sunset,temperature_2m_max,temperature_2m_min,precipitation_sum"
            "&timezone=auto"
        )
        req_w = urllib.request.Request(weather_url, headers={"User-Agent": "ADK-Agent/1.0"})
        with urllib.request.urlopen(req_w) as resp:
            weather_data = json.loads(resp.read().decode("utf-8"))

        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})

        c_temp = current.get("temperature_2m", 22.0)
        f_temp = (c_temp * 9 / 5) + 32
        humidity = current.get("relative_humidity_2m", 60)

        max_c = daily.get("temperature_2m_max", [c_temp])[0]
        min_c = daily.get("temperature_2m_min", [c_temp])[0]
        max_f = (max_c * 9 / 5) + 32
        min_f = (min_c * 9 / 5) + 32

        sunsets = daily.get("sunset", ["N/A"])
        sunset_raw = sunsets[0] if sunsets else "N/A"
        sunset_time = sunset_raw.split("T")[-1] if "T" in sunset_raw else sunset_raw
        precip = daily.get("precipitation_sum", [0.0])[0]

        country_suffix = f", {country}" if country else ""
        weather_note = (
            "Clear skies expected—ideal for private sunset dinners and beach vow renewals!"
            if precip < 2.0
            else "Passing showers likely—covered oceanfront pavilion dining recommended."
        )

        return (
            f"--- Live Weather & Sunset Outlook for {loc_name}{country_suffix} ---\n"
            f"• Current Temperature: {c_temp:.1f}°C ({f_temp:.1f}°F)\n"
            f"• Today's High / Low: {max_c:.1f}°C / {min_c:.1f}°C ({max_f:.1f}°F / {min_f:.1f}°F)\n"
            f"• Relative Humidity: {humidity}%\n"
            f"• Local Sunset Time: {sunset_time} local time (Perfect for planning sunset celebrations!)\n"
            f"• Expected Daily Precipitation: {precip:.1f} mm\n"
            f"• Romantic Planning Tip: {weather_note}"
        )
    except Exception as e:
        return f"Unable to retrieve live weather for '{destination_name}': {str(e)}"


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


def list_saved_itineraries(max_budget: float = None, milestone_years: int = None) -> str:
    """Lists saved anniversary itineraries from the Firestore database backend.

    Args:
        max_budget: Optional maximum cost filter in USD.
        milestone_years: Optional anniversary milestone filter (e.g. 25 for Silver Anniversary).

    Returns:
        A formatted string listing the saved itineraries matching the criteria.
    """
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)
    docs = collection.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        cost = data.get("total_cost", 0.0)
        m_years = data.get("milestone_years")

        if max_budget and cost > max_budget:
            continue
        if milestone_years and m_years != milestone_years:
            continue

        highlights_str = ", ".join(data.get("highlights", []))
        results.append(
            f"• [{data.get('itinerary_id', doc.id)}] {data.get('title')}\n"
            f"  - Destination: {data.get('destination')}\n"
            f"  - Milestone: {data.get('milestone_years')}th Anniversary\n"
            f"  - Cost: ${cost:,.2f} (Duration: {data.get('duration_days')} days)\n"
            f"  - Highlights: {highlights_str}\n"
            f"  - Notes: {data.get('notes', 'N/A')}"
        )

    if not results:
        return "No saved itineraries found matching your criteria in Firestore."

    return "--- Saved Anniversary Itineraries in Firestore ---\n" + "\n\n".join(results)


def save_anniversary_itinerary(title: str, destination: str, milestone_years: int, total_cost: float, duration_days: int, highlights: list[str], notes: str = "") -> str:
    """Saves a new anniversary trip itinerary into the Firestore database backend.

    Args:
        title: Name of the itinerary (e.g., "25th Silver Anniversary Maui Luxury Getaway").
        destination: Location of the trip (e.g., "Wailea, Maui, Hawaii").
        milestone_years: Milestone anniversary year (e.g., 25).
        total_cost: Total estimated cost in USD.
        duration_days: Number of days/nights.
        highlights: Key romantic activities or package highlights.
        notes: Special notes such as dietary preferences or view desires.

    Returns:
        A confirmation string with the generated itinerary ID.
    """
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    itinerary_id = f"itinerary_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

    doc_data = {
        "itinerary_id": itinerary_id,
        "title": title,
        "milestone_years": milestone_years,
        "destination": destination,
        "total_cost": total_cost,
        "max_budget": total_cost + 500.0,
        "duration_days": duration_days,
        "highlights": highlights,
        "notes": notes,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    collection.document(itinerary_id).set(doc_data)

    return (
        f"✅ Successfully saved itinerary '{title}' to Firestore!\n"
        f"• Itinerary ID: {itinerary_id}\n"
        f"• Destination: {destination}\n"
        f"• Estimated Cost: ${total_cost:,.2f}\n"
        f"• Saved to Collection: '{COLLECTION_NAME}' (Project: {PROJECT_ID})"
    )


def get_itinerary_details(itinerary_id: str) -> str:
    """Retrieves detailed information for a specific saved itinerary from Firestore by its ID.

    Args:
        itinerary_id: The ID of the itinerary document (e.g. 'itinerary_001').

    Returns:
        A string containing full details of the itinerary document from Firestore.
    """
    db = firestore.Client(project=PROJECT_ID)
    doc_ref = db.collection(COLLECTION_NAME).document(itinerary_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Itinerary ID '{itinerary_id}' was not found in Firestore."

    data = doc.to_dict()
    highlights_str = "\n  • ".join(data.get("highlights", []))

    return (
        f"--- Firestore Itinerary Details [{itinerary_id}] ---\n"
        f"• Title: {data.get('title')}\n"
        f"• Destination: {data.get('destination')}\n"
        f"• Milestone: {data.get('milestone_years')}th Anniversary\n"
        f"• Total Cost: ${data.get('total_cost', 0.0):,.2f}\n"
        f"• Duration: {data.get('duration_days')} days\n"
        f"• Highlights:\n  • {highlights_str}\n"
        f"• Notes: {data.get('notes', 'None')}\n"
        f"• Last Updated: {data.get('updated_at', 'N/A')}"
    )


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME
    ),
    instruction=a2ui_system_prompt,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        generate_anniversary_concept_art,
        generate_anniversary_video_teaser,
        get_destination_weather,
        search_anniversary_packages,
        calculate_itemized_budget,
        get_special_milestone_experiences,
        list_saved_itineraries,
        save_anniversary_itinerary,
        get_itinerary_details,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
