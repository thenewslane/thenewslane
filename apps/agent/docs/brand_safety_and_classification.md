# Brand Safety and Classification Nodes

This document describes the brand safety and classification nodes implemented for theNewslane AI pipeline.

## Brand Safety Node

**Location**: `nodes/brand_safety.py`

The Brand Safety Node implements a two-tier filtering system to ensure content is appropriate for mainstream advertisers.

### Two-Tier Filtering System

#### Tier 1: KeywordFilter
- **Purpose**: Fast keyword-based blocklist filtering
- **Data Source**: Supabase `config` table with key `keyword_blocklist`
- **Process**: Case-insensitive matching against topic title and headline cluster
- **Performance**: Instant (no API calls)
- **Short-circuits**: Yes - if blocked, stops processing

#### Tier 2: LlamaGuardFilter (DISABLED)
- **Status**: ⚠️ **DISABLED** due to API access issues and over-rejection
- **Reason**: Llama Guard was rejecting too much valid content
- **Impact**: Reduced API costs, improved pass-through rate
- **Note**: Topics skip this tier entirely (always passes)

#### Tier 3: BrandSafetyLLMFilter
- **Purpose**: Brand advertiser suitability assessment
- **API**: Anthropic Claude Haiku (`claude-3-haiku-20240307`)
- **Context**: Evaluates if Toyota/P&G would advertise next to content
- **Performance**: ~1-2 seconds per topic
- **Response**: SAFE/UNSAFE with explanation

### Usage

```python
from nodes import check_brand_safety

state = {
    "batch_id": "batch_123",
    "topics": [
        {
            "id": "topic_1",
            "title": "AI Innovation Breakthrough", 
            "headline_cluster": "New chatbot capabilities announced"
        }
    ]
}

result = check_brand_safety(state)
# Returns: {"topics": [...], "topics_rejected": int}
```

### Database Logging

All brand safety decisions are logged to the `brand_safety_log` table with:
- Tier-by-tier results
- Blocked keywords, flagged categories, explanations
- Timestamps and batch tracking
- Final pass/fail decision

### Configuration

Required environment variables:
- `GROQ_API_KEY` - for Llama Guard (Tier 2)
- `ANTHROPIC_API_KEY` - for Claude Haiku (Tier 3)

Keyword blocklist configuration:
```sql
-- Add to Supabase config table
INSERT INTO config (key, value, description) VALUES (
    'keyword_blocklist', 
    '["violence", "inappropriate", "spam"]'::jsonb,
    'Keywords that trigger immediate content blocking'
);
```

## Classification Node

**Location**: `nodes/classification_node.py`

The Classification Node categorizes brand-safe topics into predefined categories using Claude Haiku 3.5.

### Categories

The system classifies topics into exactly one of these 10 categories:

1. **Technology** - AI, software, gadgets, tech companies
2. **Politics** - Elections, government, policy, political figures
3. **Business & Finance** - Markets, economics, companies, trade
4. **Entertainment** - Movies, TV, music, celebrities, gaming
5. **Sports** - All sports, athletes, competitions, leagues
6. **Science & Health** - Medical, research, discoveries, wellness
7. **World News** - International events, conflicts, disasters
8. **Lifestyle** - Fashion, food, travel, culture, relationships
9. **Environment** - Climate, sustainability, nature, conservation
10. **Education** - Schools, learning, academic research

### Usage

```python
from nodes import classify_topics

state = {
    "batch_id": "batch_123",
    "topics": [
        {
            "id": "topic_1",
            "title": "New iPhone Released",
            "headline_cluster": "Apple announces latest smartphone"
        }
    ]
}

result = classify_topics(state)
# Returns topics with added "category" field
```

### Batch Processing

The node processes all topics in a single batch to minimize latency and API costs. Each topic receives exactly one category assignment.

### Error Handling

- **Invalid categories**: Falls back to "World News"
- **API errors**: Returns original topics without categories
- **Missing titles**: Skips classification for that topic
- **Fuzzy matching**: Handles slight variations in category names

### Configuration

Required environment variables:
- `ANTHROPIC_API_KEY` - for Claude Haiku classification

## Integration with LangGraph

Both nodes are designed as LangGraph node functions that:

1. Accept a `state` dictionary with `batch_id` and `topics`
2. Process topics according to their specific logic
3. Return updated state with processed topics
4. Maintain logging and error handling
5. Support pipeline orchestration

### Example Pipeline Integration

```python
from langgraph import StateGraph
from nodes import check_brand_safety, classify_topics

# Define your graph
graph = StateGraph()

# Add nodes
graph.add_node("brand_safety", check_brand_safety)
graph.add_node("classification", classify_topics)

# Define flow: brand safety → classification
graph.add_edge("brand_safety", "classification")

# Compile and run
pipeline = graph.compile()
result = pipeline.invoke({
    "batch_id": "batch_123",
    "topics": your_topics
})
```

## Performance Considerations

### Brand Safety Node
- **Tier 1**: Instant (keyword lookup)
- **Tier 2**: ~1-2s per topic (Groq API)
- **Tier 3**: ~1-2s per topic (Anthropic API)
- **Total**: ~2-4s per topic (with short-circuiting)

### Classification Node
- **Processing**: ~0.5-1s per topic (Anthropic API)
- **Batch optimization**: Processes sequentially but efficiently
- **Future enhancement**: HTTP batch API for true parallelization

## Database Schema Requirements

### brand_safety_log table
```sql
CREATE TABLE brand_safety_log (
    id UUID PRIMARY KEY,
    batch_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    topic_title TEXT,
    headline_cluster TEXT,
    created_at TIMESTAMPTZ,
    tier1_passed BOOLEAN,
    tier1_blocked_keyword TEXT,
    tier2_passed BOOLEAN,
    tier2_flagged_categories JSONB,
    tier3_passed BOOLEAN,
    tier3_explanation TEXT,
    overall_passed BOOLEAN
);
```

### config table
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value JSONB,
    description TEXT
);
```