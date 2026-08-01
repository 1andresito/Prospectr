# analysis.py
from providers.registry import call_provider, call_provider_streaming

def build_prompt(name, address, has_website=False, has_photos=True, has_reviews=True, has_phone=True):
    website_status = (
        "No website is listed on Google"
        if not has_website
        else "A website is listed on Google (review it as part of your research)"
    )
    gaps = []
    if not has_photos:
        gaps.append("no photos are listed on its Google Business Profile")
    if not has_reviews:
        gaps.append("it has no reviews on Google yet")
    if not has_phone:
        gaps.append("no phone number is listed on Google")
    gaps_line = (
        f"- Other known gaps: {'; '.join(gaps)}\n" if gaps else ""
    )

    return f"""
        You are an expert local business growth consultant, digital marketing strategist,
        website auditor, local SEO specialist, social media strategist, and automation consultant.

        Your task is to analyze the publicly available online presence of the following business
        and produce a complete, practical report showing how it can attract more customers,
        generate more leads, and improve its online visibility.

        BUSINESS INFORMATION:
        - Business name: {name}
        - Address: {address}
        - Current website status: {website_status}
{gaps_line}

        Use the business name and address to research the business online. Review all publicly
        available information you can find, including:

        - Google Business Profile
        - Google Maps presence
        - Google search results
        - Social media profiles
        - Online reviews
        - Business directories
        - Competitor websites
        - Local search rankings
        - Any other relevant public sources

        Do not ask me any follow-up questions. Complete the analysis using the information
        available online. If something cannot be confirmed, clearly state that it could not
        be verified instead of inventing information.

        Analyze the following areas:

        1. BUSINESS OVERVIEW

        Determine:

        - What services or products the business appears to offer
        - Who its likely target customers are
        - What city or service area it serves
        - Whether its services are clearly explained online
        - Whether it has a clear competitive advantage
        - Whether potential customers can quickly understand why they should choose this business

        2. WEBSITE OPPORTUNITY

        {"Since no website is currently listed on Google, explain" if not has_website else "A website is listed on Google. Review it and explain"}:

        - Whether the business appears to have a website elsewhere
        - Whether it should build a new website or improve its existing one
        - What pages the website should contain
        - What information should appear on the homepage
        - What calls to action should be used
        - Whether it needs online booking, quote requests, contact forms, live chat, or click-to-call buttons
        - What trust signals should be included
        - What local SEO elements should be built into the website
        - What type of content would help the website generate leads

        Recommend a practical website structure specifically for this business.

        3. GOOGLE BUSINESS PROFILE AUDIT

        Analyze the business's Google Business Profile, if available.

        Review:

        - Business name
        - Address
        - Phone number
        - Primary and secondary categories
        - Business description
        - Hours
        - Service areas
        - Services or products
        - Photos and videos
        - Review quantity
        - Review quality
        - Review frequency
        - Owner responses to reviews
        - Google Posts
        - Questions and answers
        - Booking or appointment links
        - Profile completeness

        Recommend specific changes that could improve its visibility in Google Maps and local
        search results.

        4. LOCAL SEO ANALYSIS

        Identify search terms potential customers may use to find this business.

        Include search phrases such as:

        - "[service] near me"
        - "[service] in [city]"
        - "best [business type] in [city]"
        - "[service] company in [city]"

        Determine:

        - Whether the business appears in local search results
        - Which competitors appear more prominently
        - Which services and locations the business should target
        - Whether its name, address, and phone number are consistent across directories
        - Which business directories it should be listed on
        - Whether it needs local service pages
        - Whether it needs backlinks or local partnerships
        - Whether blog or educational content would be useful

        Provide at least 10 relevant local keywords or content topics.

        5. SOCIAL MEDIA AUDIT

        Find and review any Facebook, Instagram, TikTok, LinkedIn, YouTube, or other relevant
        social profiles.

        Analyze:

        - Whether the profiles are complete
        - Whether branding is consistent
        - Posting frequency
        - Content quality
        - Engagement
        - Calls to action
        - Contact information
        - Whether the content is likely to generate customers
        - Whether the business is using photos, videos, testimonials, or customer success stories

        Recommend:

        - Which platforms the business should prioritize
        - Which platforms are probably unnecessary
        - How often it should post
        - What types of content it should publish
        - At least 10 specific social media post ideas
        - At least 3 promotional campaign ideas

        6. ONLINE REVIEWS AND REPUTATION

        Analyze reviews on Google and any other relevant platforms.

        Determine:

        - Average rating
        - Approximate number of reviews
        - Common positive feedback
        - Common complaints
        - Whether the business responds to reviews
        - Whether competitors have more or better reviews
        - Whether negative reviews reveal repeated business problems

        Recommend a practical system for:

        - Requesting reviews
        - Responding to reviews
        - Handling negative feedback
        - Increasing review frequency
        - Using positive reviews in marketing

        7. COMPETITOR ANALYSIS

        Identify 3 to 5 nearby competitors.

        Compare the business against them based on:

        - Website quality
        - Google Maps presence
        - Search visibility
        - Review count and rating
        - Social media activity
        - Services offered
        - Promotions
        - Trust signals
        - Online booking or quote requests
        - Branding
        - Content quality

        Explain:

        - What competitors are doing better
        - What this business could copy or improve
        - What opportunities competitors are missing
        - How this business could stand out

        8. LEAD GENERATION OPPORTUNITIES

        Identify realistic ways this business could generate more customers.

        Consider:

        - A new website
        - Google Business Profile optimization
        - Local SEO
        - Google Ads
        - Google Local Services Ads
        - Facebook and Instagram Ads
        - Retargeting
        - Referral programs
        - Email marketing
        - SMS marketing
        - Seasonal promotions
        - Partnerships with nearby businesses
        - Community involvement
        - Lead magnets
        - Coupons or introductory offers
        - Customer reactivation campaigns

        Only recommend strategies that make sense for this specific type of business.

        9. CONVERSION AND CUSTOMER EXPERIENCE

        Evaluate how easy it is for a potential customer to:

        - Find the business
        - Understand its services
        - Trust the business
        - Call the business
        - Send a message
        - Request a quote
        - Book an appointment
        - Find its hours and location
        - Receive a follow-up

        Identify anything that may cause potential customers to choose a competitor instead.

        10. AUTOMATION OPPORTUNITIES

        Identify repetitive marketing, sales, and customer service tasks that could be automated.

        Consider:

        - Missed-call text-back
        - Website lead capture
        - AI chatbot
        - Appointment scheduling
        - Lead qualification
        - Quote request follow-up
        - Email follow-up
        - SMS follow-up
        - Appointment reminders
        - Review requests
        - Customer reactivation
        - Social media scheduling
        - CRM updates
        - Monthly reporting

        For each recommended automation, explain:

        - The problem it solves
        - How it would work
        - The expected benefit
        - The implementation difficulty: Easy, Moderate, or Advanced

        FINAL RESPONSE FORMAT:

        Organize the final report using these sections:

        ## 1. Executive Summary

        Give a concise summary of the business's current online presence, biggest weaknesses,
        and strongest opportunities for getting more customers.

        ## 2. Confirmed Business Information

        List the information you were able to verify, including:

        - Business name
        - Address
        - Phone number
        - Business category
        - Services
        - Website
        - Google Business Profile
        - Social profiles
        - Review platforms

        Clearly mark anything that could not be verified.

        ## 3. Online Presence Scorecard

        Create a table with scores from 1 to 10 for:

        - Website
        - Google Business Profile
        - Local SEO
        - Social media
        - Online reputation
        - Lead generation
        - Lead conversion
        - Follow-up process
        - Competitive position
        - Overall online presence

        For every score, include the main reason and the recommended improvement.

        ## 4. Complete Recommendation List

        Provide a detailed list of all meaningful recommendations.

        For each recommendation, include:

        - Problem
        - Evidence or observation
        - Recommended solution
        - Expected benefit
        - Priority: Low, Medium, High, or Critical
        - Difficulty: Easy, Moderate, or Advanced
        - Timeframe
        - One-time task or ongoing task

        ## 5. Top 10 Priorities

        Rank the 10 most important actions from highest to lowest priority.

        Prioritize actions based on:

        - Potential to generate qualified leads
        - Potential to increase conversions
        - Cost
        - Difficulty
        - Urgency
        - Long-term value

        ## 6. Quick Wins

        Separate quick improvements into:

        - Actions that can be completed within 24 hours
        - Actions that can be completed within 7 days
        - Actions that can be completed within 30 days

        ## 7. Recommended Website Structure

        Provide a suggested website sitemap and explain what each page should contain.

        ## 8. Local Keyword Ideas

        Provide at least 10 keywords or search topics the business should target.

        ## 9. Social Media Content Ideas

        Provide at least 10 specific content ideas relevant to this business.

        ## 10. 90-Day Growth Plan

        Create a practical week-by-week plan for the next 90 days.

        Include:

        - Website development
        - Google Business Profile improvements
        - Review generation
        - Local SEO
        - Social media
        - Lead generation
        - Follow-up automation
        - Performance tracking

        ## 11. Services That Could Be Sold to This Business

        Identify services a web developer, marketer, or automation agency could offer.

        For each service, include:

        - Service name
        - Problem it solves
        - Deliverables
        - Expected outcome
        - One-time project or monthly service
        - Suggested pricing model, without assuming the business's exact budget

        ## 12. Personalized Outreach Message

        Write a short, natural outreach message to the business owner.

        The message must:

        - Mention 2 or 3 genuine observations from the research
        - Avoid insulting or criticizing the owner
        - Explain one important opportunity
        - Offer a simple next step
        - Avoid unrealistic promises
        - Sound personally written rather than automated

        IMPORTANT RULES:

        - Do not ask follow-up questions.
        - Do not invent missing business information.
        - Use only publicly available information.
        - Make recommendations specific to this business.
        - Avoid generic advice that could apply to any company.
        - Explain why each recommendation matters.
        - Include sources or URLs for important observations when possible.
        - Do not guarantee rankings, customers, leads, or revenue.
        - Do not contact the business or submit any forms.
        - Keep the report practical, organized, and focused on getting more customers.
        """

def generate_marketing_analysis(name, address, provider, api_key, has_website=False, has_photos=True, has_reviews=True, has_phone=True):
    prompt = build_prompt(name, address, has_website, has_photos, has_reviews, has_phone)
    return call_provider(provider, prompt, api_key)


def generate_marketing_analysis_stream(name, address, provider, api_key, has_website=False, has_photos=True, has_reviews=True, has_phone=True):
    prompt = build_prompt(name, address, has_website, has_photos, has_reviews, has_phone)
    yield from call_provider_streaming(provider, prompt, api_key)