"""
Temporal Relational Reasoning (TRR) Prompt Synthesizer.
Formats Knowledge Graph tuples and quantitative market data into LLM context.
"""

from typing import Any

from modules.reasoning.models.schema import MarketData


def build_trr_prompt(
    symbol: str, 
    target_date: str, 
    graph_data: list[dict[str, Any]], 
    market_data: list[MarketData]
) -> list[dict[str, str]]:
    """
    Constructs the OpenAI-compatible message array for the vLLM chat completion.
    """
    
    # 1. System Prompt: Defines the persona and strict output constraints
    system_prompt = """You are an expert quantitative financial analyst AI.
Your task is to predict the short-term trend of a specific stock based on a Temporal Knowledge Graph of recent events and recent market price action.

OUTPUT REQUIREMENTS:
You must output your decision strictly as a JSON object matching this exact schema, with no additional text or markdown formatting outside the JSON:
{
    "symbol": "TICKER",
    "target_date": "YYYY-MM-DD",
    "trend": "Bullish" | "Bearish" | "Sideways",
    "confidence": 0.0 to 1.0,
    "reasoning": "1-2 concise sentences explaining the primary driver."
}"""

    # 2. Format the Graph Context
    if not graph_data:
        graph_text = "No recent impactful news or social events found in the knowledge graph for this period."
    else:
        graph_lines = []
        for item in graph_data:
            # Format: [Date] Subject --[Relation]--> Object (Attention: X)
            line = f"[{item['date']}] {item['subject_type']} '{item['subject']}' --[{item['relation']}]--> {item['object']} (Attention Weight: {item['attention_score']})"
            graph_lines.append(line)
        graph_text = "\n".join(graph_lines)

    # 3. Format the Market Context
    if not market_data:
        market_text = "No recent market data available."
    else:
        market_lines = []
        for md in market_data:
            line = f"- {md.date}: Close: {md.close:.2f} | Return: {md.daily_return*100:.2f}% | Vol: {md.volume:.2f}x avg"
            market_lines.append(line)
        market_text = "\n".join(market_lines)

    # 4. User Prompt: Assembles the sections as requested
    user_prompt = f"""Target Stock: {symbol}
Target Date: {target_date}

=== GENERAL CONTEXT ===
Analyze the following temporal knowledge graph (recent events ranked by attention/decay) and market data leading up to the target date. Higher attention weights indicate more recent and impactful events.

=== EXAMPLES ===
Input Graph:
[2026-08-01] NEWS 'Company announces record Q3 profits' --[MENTIONS]--> FPT (Attention Weight: 0.95)
[2026-07-28] POST 'Retail investors panicking over CEO resignation' --[SENTIMENT_NEGATIVE]--> FPT (Attention Weight: 0.40)
Input Market:
- 2026-08-01: Close: 130.50 | Return: 2.50% | Vol: 1.80x avg
Output:
{{
    "symbol": "FPT",
    "target_date": "2026-08-02",
    "trend": "Bullish",
    "confidence": 0.85,
    "reasoning": "Strong Q3 earnings announcement outweighs older negative sentiment, supported by a 2.5% price surge on high volume."
}}

=== GRAPH CONTEXT ===
{graph_text}

=== MARKET CONTEXT ===
{market_text}

=== FINAL REQUIREMENT ===
Based on the Graph Context and Market Context above, predict the trend for {symbol} on {target_date}. 
Output ONLY valid JSON matching the required schema."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]