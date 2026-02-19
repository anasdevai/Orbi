import asyncio, sys, traceback
from server.agents.planner import generate_plan

async def test():
    try:
        plan = await generate_plan(
            user_message=(
                "Optimize the SEO of my LinkedIn profile. "
                "Read my current headline, about section, experience descriptions, and skills. "
                "Then apply keyword-rich improvements to each section."
            ),
            agent_name="Page Summarizer",
            agent_description="Reads and summarizes web pages",
            tab_url='https://www.linkedin.com/in/me',
            available_tools=['read_page', 'get_page_text', 'click_element', 'type_text', 'scroll_page', 'navigate_to']
        )
        print(f"\n=== GENERATED PLAN ({len(plan)} steps) ===", flush=True)
        for i, todo in enumerate(plan, 1):
            print(f"  Step {i}: {todo['title']}", flush=True)
        print("=== END OF PLAN ===", flush=True)
    except Exception as e:
        print(f"EXCEPTION: {e}", flush=True)
        traceback.print_exc()

asyncio.run(test())
