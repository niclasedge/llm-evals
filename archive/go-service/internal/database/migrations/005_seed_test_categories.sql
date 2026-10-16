-- Seed data migration for test categories
-- Populates test_categories table with predefined test types and templates

-- 1. CODING Category
INSERT OR REPLACE INTO test_categories (
    id, name, display_name, description,
    template_prompt, default_parameters, scoring_criteria,
    allowed_models, timeout_seconds,
    icon, color, tags, status, version
) VALUES (
    1, 'coding', 'Programming & Algorithms',
    'Programming challenges, algorithm implementation, and code generation tasks',
    
    -- Template prompt with variables
    'Write a {language} function that {task_description}. 

Requirements:
- Function should be named `{function_name}`
- {additional_requirements}
- Include proper error handling
- Add comments explaining the approach

Example usage:
{usage_example}',
    
    -- Default parameters (JSON)
    '{"temperature": 0.1, "max_tokens": 1500, "top_p": 0.9, "stop_sequences": ["```"]}',
    
    -- Scoring criteria (JSON)
    '{
        "correctness": {"weight": 0.4, "description": "Code produces correct output"},
        "efficiency": {"weight": 0.2, "description": "Algorithm complexity and performance"},
        "readability": {"weight": 0.2, "description": "Code clarity and documentation"},
        "error_handling": {"weight": 0.1, "description": "Proper error management"},
        "best_practices": {"weight": 0.1, "description": "Language conventions and patterns"}
    }',
    
    -- Allowed models (JSON)
    '{"models": ["llama3.2:3b", "gemma3:27b", "qwen2.5-coder", "deepseek-r1:8b"]}',
    
    300, -- timeout_seconds
    'code', '#3B82F6', -- icon, color (blue)
    '{"tags": ["programming", "algorithms", "development", "software"]}',
    'active', '1.0'
);

-- 2. REASONING Category
INSERT OR REPLACE INTO test_categories (
    id, name, display_name, description,
    template_prompt, default_parameters, scoring_criteria,
    allowed_models, timeout_seconds,
    icon, color, tags, status, version
) VALUES (
    2, 'reasoning', 'Logic & Analytical Thinking',
    'Logical reasoning, problem-solving, and analytical thinking challenges',
    
    -- Template prompt
    'Analyze the following scenario and provide a well-reasoned response:

Scenario: {scenario}

Please provide:
1. Your analysis of the situation
2. Key factors to consider
3. Logical reasoning for your conclusion
4. Any assumptions made

Question: {question}

Think through this step-by-step and explain your reasoning clearly.',
    
    -- Default parameters (JSON)
    '{"temperature": 0.3, "max_tokens": 1200, "top_p": 0.95}',
    
    -- Scoring criteria (JSON)
    '{
        "logical_consistency": {"weight": 0.3, "description": "Internal logic and consistency"},
        "depth_of_analysis": {"weight": 0.25, "description": "Thoroughness of examination"},
        "evidence_usage": {"weight": 0.2, "description": "Use of provided information"},
        "clarity": {"weight": 0.15, "description": "Clear communication of reasoning"},
        "conclusion_validity": {"weight": 0.1, "description": "Soundness of final conclusion"}
    }',
    
    -- Allowed models
    '{"models": ["llama3.2:3b", "gemma3:27b", "phi4-reasoning", "deepseek-r1:8b"]}',
    
    240, -- timeout_seconds
    'brain', '#8B5CF6', -- icon, color (purple)
    '{"tags": ["logic", "analysis", "critical-thinking", "problem-solving"]}',
    'active', '1.0'
);

-- 3. CREATIVE Category
INSERT OR REPLACE INTO test_categories (
    id, name, display_name, description,
    template_prompt, default_parameters, scoring_criteria,
    allowed_models, timeout_seconds,
    icon, color, tags, status, version
) VALUES (
    3, 'creative', 'Creative Writing & Ideation',
    'Creative writing, storytelling, brainstorming, and imaginative content generation',
    
    -- Template prompt
    'Create a {content_type} based on the following prompt:

Theme: {theme}
Style: {style}
Target audience: {audience}
Length: {length_requirement}

Additional constraints:
{constraints}

Be creative and engaging while staying true to the theme and style requirements.',
    
    -- Default parameters (JSON)
    '{"temperature": 0.8, "max_tokens": 2000, "top_p": 0.9, "frequency_penalty": 0.1}',
    
    -- Scoring criteria (JSON)
    '{
        "creativity": {"weight": 0.3, "description": "Originality and imaginative content"},
        "engagement": {"weight": 0.25, "description": "Ability to capture and hold interest"},
        "theme_adherence": {"weight": 0.2, "description": "Staying true to given theme"},
        "style_consistency": {"weight": 0.15, "description": "Maintaining consistent style"},
        "language_quality": {"weight": 0.1, "description": "Grammar, vocabulary, and flow"}
    }',
    
    -- Allowed models
    '{"models": ["llama3.2:3b", "gemma3:27b", "mistral-small3.2"]}',
    
    180, -- timeout_seconds
    'palette', '#EC4899', -- icon, color (pink)
    '{"tags": ["creativity", "writing", "storytelling", "brainstorming"]}',
    'active', '1.0'
);

-- 4. TOOL-CALLING Category
INSERT OR REPLACE INTO test_categories (
    id, name, display_name, description,
    template_prompt, default_parameters, scoring_criteria,
    allowed_models, timeout_seconds,
    icon, color, tags, status, version
) VALUES (
    4, 'tool-calling', 'Function & API Usage',
    'Function calling, API integration, and tool utilization tasks',
    
    -- Template prompt
    'You have access to the following tools/functions:

{available_tools}

Task: {task_description}

Use the appropriate tools to complete this task. Consider:
- Which tools are most relevant for this task
- The correct order of operations
- How to handle potential errors or edge cases
- How to combine results from multiple tools if needed

Please provide your solution step-by-step.',
    
    -- Default parameters (JSON)
    '{"temperature": 0.2, "max_tokens": 1000, "top_p": 0.9}',
    
    -- Scoring criteria (JSON)
    '{
        "tool_selection": {"weight": 0.3, "description": "Choosing appropriate tools"},
        "execution_accuracy": {"weight": 0.25, "description": "Correct tool usage and parameters"},
        "error_handling": {"weight": 0.2, "description": "Managing errors and edge cases"},
        "efficiency": {"weight": 0.15, "description": "Optimal sequence and resource usage"},
        "result_validation": {"weight": 0.1, "description": "Verifying and presenting results"}
    }',
    
    -- Allowed models
    '{"models": ["llama3.2:3b", "gemma3:27b", "qwen2.5-coder"]}',
    
    120, -- timeout_seconds
    'tool', '#10B981', -- icon, color (green)
    '{"tags": ["tools", "functions", "api", "integration"]}',
    'active', '1.0'
);

-- Add subcategories for coding
INSERT OR REPLACE INTO test_categories (
    id, name, display_name, description, parent_category_id,
    category_path, sort_order,
    template_prompt, default_parameters, scoring_criteria,
    timeout_seconds, icon, color, tags, status, version
) VALUES 
(101, 'algorithms', 'Algorithms', 'Algorithm design and implementation', 1, 'coding/algorithms', 1,
 'Implement the {algorithm_name} algorithm in {language}. The algorithm should {requirements}.

Requirements:
- Function name: {function_name}
- Input: {input_format}
- Output: {output_format}
- Time complexity: {complexity_requirement}

Please include:
- Clear variable names
- Step-by-step comments
- Edge case handling
- Example usage', 
 '{"temperature": 0.05, "max_tokens": 1200, "top_p": 0.9}', 
 '{"correctness": {"weight": 0.5, "description": "Algorithm correctness"}, "efficiency": {"weight": 0.3, "description": "Time and space complexity"}, "clarity": {"weight": 0.2, "description": "Code readability"}}',
 300, 'cpu', '#3B82F6', '{"tags": ["algorithms", "complexity", "optimization"]}', 'active', '1.0'),

(102, 'data-structures', 'Data Structures', 'Data structure implementation and usage', 1, 'coding/data-structures', 2,
 'Create a {data_structure} class in {language} with the following operations:

Required operations:
{operations}

Requirements:
- Class name: {class_name}
- Efficient implementation
- Proper error handling
- Thread safety (if applicable)

Include test examples demonstrating all operations.', 
 '{"temperature": 0.1, "max_tokens": 1500, "top_p": 0.9}', 
 '{"implementation": {"weight": 0.4, "description": "Correct implementation"}, "efficiency": {"weight": 0.3, "description": "Operation efficiency"}, "design": {"weight": 0.3, "description": "API design and usability"}}',
 300, 'database', '#3B82F6', '{"tags": ["data-structures", "implementation", "collections"]}', 'active', '1.0'),

(103, 'debugging', 'Code Debugging', 'Finding and fixing code issues', 1, 'coding/debugging', 3,
 'Debug the following {language} code and fix the issue(s):

```{language}
{buggy_code}
```

The code is supposed to {expected_behavior}, but instead it {actual_behavior}.

Please:
1. Identify the bug(s)
2. Explain why the bug occurs
3. Provide the corrected code
4. Explain your fix', 
 '{"temperature": 0.15, "max_tokens": 1000, "top_p": 0.9}', 
 '{"identification": {"weight": 0.3, "description": "Correctly identifying bugs"}, "explanation": {"weight": 0.3, "description": "Explaining the cause"}, "fix": {"weight": 0.4, "description": "Providing correct solution"}}',
 240, 'bug', '#F59E0B', '{"tags": ["debugging", "troubleshooting", "analysis"]}', 'active', '1.0'),

-- Add subcategories for reasoning
(201, 'logical-reasoning', 'Logical Reasoning', 'Formal logic and deductive reasoning', 2, 'reasoning/logical-reasoning', 1,
 'Given the following logical premises:

{premises}

Question: {question}

Please provide:
1. Your logical analysis
2. Step-by-step deduction
3. Final conclusion
4. Confidence level in your answer',
 '{"temperature": 0.2, "max_tokens": 800, "top_p": 0.95}',
 '{"logic": {"weight": 0.4, "description": "Logical validity"}, "deduction": {"weight": 0.3, "description": "Deductive reasoning"}, "clarity": {"weight": 0.3, "description": "Clear explanation"}}',
 180, 'logic', '#8B5CF6', '{"tags": ["logic", "deduction", "formal-reasoning"]}', 'active', '1.0'),

(202, 'mathematical-reasoning', 'Mathematical Reasoning', 'Mathematical problem solving and proofs', 2, 'reasoning/mathematical-reasoning', 2,
 'Solve the following mathematical problem:

{problem_statement}

Given information:
{given_data}

Please provide:
1. Problem analysis
2. Solution approach
3. Step-by-step solution
4. Verification of your answer',
 '{"temperature": 0.1, "max_tokens": 1000, "top_p": 0.9}',
 '{"accuracy": {"weight": 0.4, "description": "Mathematical accuracy"}, "method": {"weight": 0.3, "description": "Solution approach"}, "clarity": {"weight": 0.3, "description": "Clear explanation"}}',
 240, 'calculator', '#8B5CF6', '{"tags": ["mathematics", "problem-solving", "proofs"]}', 'active', '1.0');