from typing import List

class Prompt:

    def _create_compression_prompt(self, 
                                 original_tokens,
                                 content: str, 
                                 target_modules: List[str], 
                                 target_tokens: int) -> str:
        """Create XML compression prompt"""
        
        compression_ratio = target_tokens / original_tokens if original_tokens > 0 else 1.0
        
        prompt = f"""# XML Context Compression Expert

        You are a professional XML context compression expert specialized in processing multi-agent context data and outputting structured XML format.

        ## COMPRESSION REQUIREMENTS

        **Original Token Count**: {original_tokens}
        **MAXIMUM ALLOWED TOKENS**: {target_tokens} ⚠️ HARD LIMIT ⚠️
        **Compression Ratio**: {compression_ratio:.2f}
        **Priority Sections for Compression**: {', '.join(target_modules)}

        ## XML OUTPUT FORMAT

        You MUST output in this exact XML structure:

        ```xml
        <context>
            <BACKGROUND>
                <system_prompt></system_prompt>
                <task></task>
                <knowledge></knowledge>
                <external_knowledge></external_knowledge>
            </BACKGROUND>

            <PLAN>
                <plan_iteration number="1">
                    <steps></steps>
                </plan_iteration>
            </PLAN>

            <SUB_APP>
                <agent name="xxxx">
                    <content></content>
                </agent>
            </SUB_APP>

            <HISTORY>
                <entry role="system">
                    
                </entry>
            </HISTORY>
        </context>
        ```

        ## COMPRESSION STRATEGY BY SECTION

        **BACKGROUND Section** ({"✓" if "BACKGROUND" in target_modules else "○"} Priority):
        - Extract only core facts and key concepts
        - Preserve main objectives

        **PLAN Section** ({"✓" if "PLAN" in target_modules else "○"} Priority):
        - Keep only key steps and final decisions
        - Remove detailed reasoning and intermediate processes
        - Keeping the last plan list and deleting the others is also a compression solution.

        **SUB_APP Section** ({"✓" if "SUB_APP" in target_modules else "○"} Priority):
        - Core findings, search results, key discoveries
        - Remove verbose API responses and metadata
        - Compress the contents of each subapp separately, retaining the contents of all apps

        **HISTORY Section** ({"✓" if "HISTORY" in target_modules else "○"} Priority):
        - Extract main conversation topics and key decision points
        - Convert dialogue to essential entries only

        ## EXECUTION RULES

        1. **Token Priority**: Meeting ≤{target_tokens} tokens is MANDATORY
        2. **XML Structure**: follow exact XML format shown above
        3. **Section Handling**: 
        - ONLY compress sections that exist in the source content
        - If a section is not present in the source, keep its XML tag empty
        - It is strictly forbidden to fabricate or supplement content for missing sections
        4. **Compression Order**: Process priority sections more aggressively
        5. **Information Density**: Be ruthlessly concise while preserving key information
        6. **Output Consistency**: Always output the four main sections, but allow them to be empty


        ## SOURCE CONTENT

        ```
        {content}
        ```

        ## EXECUTE XML COMPRESSION

        **CRITICAL**: Your output MUST be ≤{target_tokens} tokens and follow the exact XML structure.

        Process the content:
        1. **Analyze Sections**: Identify BACKGROUND, PLAN, SUB_APP, HISTORY content
        2. **Apply Compression**: Focus on priority sections {', '.join(target_modules)}
        3. **Generate XML**: Output complete <context> structure with all subsections
        4. **Verify Tokens**: Ensure final output is within token limit

        **Output ONLY the XML structure. No explanations or additional text.**"""

        return prompt

    def _create_history_compression_prompt(self, original_tokens, content_to_compress: str, target_tokens: int) -> str:
        """Create sectional compression prompt"""

        compression_ratio = target_tokens / original_tokens if original_tokens > 0 else 1.0
        
        prompt = f"""# Sectional Dialogue History Compression Expert

        You are a compression expert specialized in processing sectional dialogue history. Your task is to compress lengthy dialogue history into concise key point summaries.

        ## Compression Requirements

        **Original Token Count**: {original_tokens}
        **Target Token Count**: {target_tokens} ⚠️ Strict Limit ⚠️
        **Compression Ratio**: {compression_ratio:.2f}

        ## Key Information Extraction
        1. **Decision Points** - Extract key decisions and conclusions
        2. **Technical Details** - Retain important technical information and configurations
        3. **Problem Solving** - Record encountered problems and solutions
        4. **Progress Summary** - Summarize progress and achievements at each stage

        ## Output Format

        Please output the compressed section content as a concise summary that captures the key points, decisions, and outcomes from the dialogue history.

        ## Original Section Content

        ```
        {content_to_compress}
        ```

        ## Execute Compression

        **Important**: Output must be strictly controlled within {target_tokens} tokens, maintaining high information density and logical clarity.

        Please start compression:"""

        return prompt
    