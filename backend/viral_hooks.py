""""
Viral Hook Generator
Generates attention-grabbing hooks for social media content
Inspired by Revid AI's hook generation feature
"""

import random
from typing import Dict, List
from emergentintegrations.llm.chat import LlmChat, UserMessage
import os

# Hook templates based on viral content analysis
HOOK_TEMPLATES = {
    "question": [
        "Did you know that {fact}?",
        "What if I told you {fact}?",
        "Have you ever wondered {question}?",
        "Why do {group} always {action}?",
        "How is {thing} even possible?"
    ],
    "shocking": [
        "This {thing} will blow your mind!",
        "You won't believe what happened when {event}!",
        "The truth about {topic} that nobody tells you",
        "This changes everything we know about {topic}",
        "Scientists discovered something incredible about {topic}"
    ],
    "urgency": [
        "Stop {action} immediately! Here's why...",
        "If you're still {action}, you need to see this",
        "This is your last chance to {action}",
        "Don't miss out on {opportunity}",
        "Time is running out for {thing}"
    ],
    "curiosity": [
        "The secret {group} doesn't want you to know",
        "I tried {action} for 30 days, here's what happened",
        "The real reason why {thing} happens",
        "What {celebrity/expert} won't tell you about {topic}",
        "This simple trick changed everything"
    ],
    "controversy": [
        "Everyone is wrong about {topic}",
        "Why {popular belief} is actually a lie",
        "The dark side of {topic} nobody talks about",
        "I'm about to expose {thing}",
        "This will make {group} angry, but it's the truth"
    ],
    "transformation": [
        "From {bad state} to {good state} in {timeframe}",
        "How I went from {start} to {end}",
        "The {number} steps that changed my {aspect}",
        "Before and after: {transformation}",
        "This {method} took me from {before} to {after}"
    ],
    "list": [
        "{number} things you didn't know about {topic}",
        "Top {number} secrets of {successful group}",
        "{number} mistakes everyone makes with {topic}",
        "{number} signs that you're {condition}",
        "{number} reasons why {statement}"
    ],
    "story": [
        "A {adjective} story about {topic}",
        "The day everything changed: {event}",
        "This happened to me and it will happen to you",
        "My biggest mistake with {topic}",
        "The moment I realized {realization}"
    ]
}

# Viral patterns
VIRAL_PATTERNS = {
    "tiktok": {
        "max_length": 150,
        "style": "short, punchy, immediate impact",
        "hooks": ["question", "shocking", "curiosity", "transformation"]
    },
    "youtube": {
        "max_length": 300,
        "style": "engaging, detailed, builds anticipation",
        "hooks": ["story", "controversy", "transformation", "list"]
    },
    "instagram": {
        "max_length": 200,
        "style": "visual, aesthetic, relatable",
        "hooks": ["transformation", "story", "curiosity", "question"]
    }
}


async def generate_viral_hook(
    topic: str,
    platform: str = "tiktok",
    hook_type: str = None,
    custom_context: str = None
) -> Dict:
    """
    Generate a viral hook for the given topic
    
    Args:
        topic: The main topic/theme
        platform: Target platform (tiktok, youtube, instagram)
        hook_type: Specific hook type or None for AI to choose
        custom_context: Additional context for personalization
    
    Returns:
        Dict with hook, explanation, and suggestions
    """
    
    # Get platform-specific settings
    platform_config = VIRAL_PATTERNS.get(platform.lower(), VIRAL_PATTERNS["tiktok"])
    
    # Build the prompt for hook generation
    prompt = f"""Generate a viral hook for social media content.

Topic: {topic}
Platform: {platform}
Style: {platform_config['style']}
Max length: {platform_config['max_length']} characters

{f'Additional context: {custom_context}' if custom_context else ''}

{f'Hook type: {hook_type}' if hook_type else 'Choose the most effective hook type for this topic'}

Generate 3 different hook variations:
1. A primary hook (most viral potential)
2. An alternative hook (different angle)
3. A backup hook (safe but effective)

For each hook, explain why it works and what psychological trigger it uses.

Format your response as JSON:
{{
    "primary": {{
        "hook": "the hook text",
        "trigger": "psychological trigger used",
        "explanation": "why this works"
    }},
    "alternative": {{
        "hook": "the hook text",
        "trigger": "psychological trigger used", 
        "explanation": "why this works"
    }},
    "backup": {{
        "hook": "the hook text",
        "trigger": "psychological trigger used",
        "explanation": "why this works"
    }},
    "tips": ["tip1", "tip2", "tip3"]
}}

Make hooks attention-grabbing, authentic, and optimized for {platform}."""

    try:
        # Use LLM to generate hooks
        llm = LlmChat(
            model="gpt-4o-mini",  # Fast and good for short-form content
            api_key=os.environ.get('EMERGENT_LLM_KEY')
        )
        
        response = llm.chat([UserMessage(content=prompt)])
        
        # Parse JSON response
        import json
        try:
            # Try to extract JSON from response
            response_text = response.choices[0].message.content
            # Find JSON in the response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                result = json.loads(response_text[start:end])
            else:
                result = json.loads(response_text)
            
            return {
                "success": True,
                "hooks": result,
                "platform": platform,
                "topic": topic
            }
        except json.JSONDecodeError:
            # Fallback: return raw response
            return {
                "success": True,
                "hooks": {
                    "primary": {
                        "hook": response_text[:platform_config['max_length']],
                        "trigger": "Generated content",
                        "explanation": "AI-generated hook"
                    }
                },
                "platform": platform,
                "topic": topic,
                "raw_response": response_text
            }
            
    except Exception as e:
        # Fallback: use template-based generation
        return generate_template_hook(topic, platform, hook_type)


def generate_template_hook(topic: str, platform: str, hook_type: str = None) -> Dict:
    """
    Fallback method using templates when AI is unavailable
    """
    platform_config = VIRAL_PATTERNS.get(platform.lower(), VIRAL_PATTERNS["tiktok"])
    
    # Choose hook types for this platform
    available_types = platform_config.get("hooks", list(HOOK_TEMPLATES.keys()))
    
    if hook_type and hook_type in HOOK_TEMPLATES:
        selected_type = hook_type
    else:
        selected_type = random.choice(available_types)
    
    # Get templates for selected type
    templates = HOOK_TEMPLATES[selected_type]
    
    # Generate 3 variations
    hooks = []
    for i in range(3):
        template = random.choice(templates)
        # Simple placeholder replacement
        hook = template.replace("{topic}", topic)
        hook = hook.replace("{thing}", topic)
        hook = hook.replace("{fact}", f"amazing fact about {topic}")
        hook = hook.replace("{question}", f"why {topic} works this way")
        
        hooks.append({
            "hook": hook[:platform_config['max_length']],
            "trigger": selected_type,
            "explanation": f"Uses {selected_type} technique to grab attention"
        })
    
    return {
        "success": True,
        "hooks": {
            "primary": hooks[0],
            "alternative": hooks[1] if len(hooks) > 1 else hooks[0],
            "backup": hooks[2] if len(hooks) > 2 else hooks[0]
        },
        "platform": platform,
        "topic": topic,
        "method": "template"
    }


async def analyze_hook_performance(hook_text: str) -> Dict:
    """
    Analyze a hook's potential viral performance
    """
    
    prompt = f"""Analyze this social media hook for viral potential:

"{hook_text}"

Provide analysis in these areas:
1. Attention Score (1-10): How well it grabs attention
2. Curiosity Score (1-10): How much it makes people want to know more
3. Emotional Impact (1-10): Strength of emotional response
4. Shareability (1-10): Likelihood people will share
5. Clarity Score (1-10): How clear and understandable it is

Also provide:
- Strengths (what works well)
- Weaknesses (what could be improved)
- Suggestions (3 ways to improve it)
- Predicted performance (low/medium/high/viral)

Format as JSON."""

    try:
        llm = LlmChat(
            model="gpt-4o-mini",
            api_key=os.environ.get('EMERGENT_LLM_KEY')
        )
        
        response = llm.chat([UserMessage(content=prompt)])
        
        import json
        response_text = response.choices[0].message.content
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start != -1 and end > start:
            result = json.loads(response_text[start:end])
            return {
                "success": True,
                "analysis": result,
                "hook": hook_text
            }
        
        return {
            "success": False,
            "error": "Could not parse analysis"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }