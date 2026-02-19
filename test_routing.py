import asyncio, sys, traceback
from server.agents.factory import build_agent, build_orchestrator
from server.db.agent_service import get_all_agents
from agents import Runner

async def test_routing():
    try:
        # Load all agents
        agent_records = await get_all_agents()
        sub_agents = [build_agent(r, "test-session") for r in agent_records]
        
        # Build orchestrator
        orchestrator = build_orchestrator(sub_agents, "https://www.linkedin.com/in/me", "test-session")
        
        # Test routing prompt
        user_message = "Optimize the SEO of my LinkedIn profile. Read my current headline and about section."
        
        print(f"\nUser Message: {user_message}")
        print("Routing...")
        
        # Use Runner.run to get the routing result
        result = Runner.run(orchestrator, input=user_message)
        
        print(f"\nRouting Response: {result.final_text}")
        
        # Check if handoff happened or if it mentioned the agent
        mention = False
        for r in agent_records:
            if r['name'].lower() in result.final_text.lower():
                print(f"SUCCESS: Routed/Recommended agent: {r['name']}")
                mention = True
                break
        
        if not mention:
            print("FAILED: No specific agent mentioned in routing response.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_routing())
