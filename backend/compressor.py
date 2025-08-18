from typing import List, Dict, Any
import xml.dom.minidom
import re
try:
    from compress_tf_idf import TextCompressor
except ImportError as e:
    # If import fails, use simplified version
    print(f"Warning: Unable to import user-provided compression module: {e}")
    print("Will use simplified version")


class ContextCompressor:
    def __init__(self, 
                 api_key=None, 
                 base_url=None,
                 model_name="gpt-4o-mini",
                 use_tf_idf=False,
                 use_history_compression=False,
                 **kwargs):
        """
        Initialize compressor
        
        Args:
            api_key: OpenAI API key
            base_url: OpenAI API base URL
            model_name: Model name
            use_tf_idf: Whether to use TF-IDF preprocessing
            use_history_compression: Whether to use history compression
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model_name = model_name
        self.use_tf_idf = use_tf_idf
        self.use_history_compression = use_history_compression
        
        # Initialize OpenAI client (if API key provided)
        if self.api_key and self.api_key.strip():
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                print("✅ LLM client initialized successfully")
            except ImportError:
                print("⚠️ OpenAI package not installed, using fallback compression")
                self.client = None
            except Exception as e:
                print(f"⚠️ Failed to initialize LLM client: {e}")
                self.client = None
        else:
            self.client = None
            
        # Initialize TF-IDF compressor
        self.tf_idf_compressor = TextCompressor()
        
        # Initialize tokenizer
        if self.client:
            try:
                import tiktoken
                try:
                    self.tokenizer = tiktoken.encoding_for_model(self.model_name)
                except KeyError:
                    self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                print("⚠️ tiktoken not installed, using simple token counting")
                self.tokenizer = None
        else:
            self.tokenizer = None
        
    def count_tokens(self, text: str) -> int:
        """Count token count"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Simplified token calculation
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
            other_chars = len(text) - chinese_chars - sum(len(word) for word in re.findall(r'\b[a-zA-Z]+\b', text))
            return int(chinese_chars * 1.5 + english_words + other_chars * 0.5)
        
    def compress_content(self, content: str, config: Dict[str, Any]) -> str:
        """
        Compress content, implementing logic according to compress_file
        Process entire XML document content, supporting target_modules (section information)
        
        Args:
            content: Entire XML document content
            config: Compression configuration, including target_modules (section information), max_token, etc.
            
        Returns:
            Compressed content
        """
        original_tokens = self.count_tokens(content)
        max_tokens = config.get('max_token', 1000)
        target_modules = config.get('target_modules', ['all'])
        use_tf_idf = config.get('use_tf_idf', False)
        use_history_compression = config.get('use_history_compression', False)
        
        if original_tokens <= max_tokens:
            return content
        
        # Calculate compression ratio
        compression_ratio = max_tokens / original_tokens if original_tokens > 0 else 1.0
        
        # Mimic compress_file logic
        processed_content = content
        
        # 1. If using TF-IDF preprocessing (for XML format)
        if use_tf_idf and self._is_xml_content(content):
            tf_idf_ratio = config.get('tf_idf_compression_ratio', 0.6)
            processed_content = self._compress_text_by_tf_idf(processed_content, target_ratio=tf_idf_ratio)
        
        # 2. If using history compression (for XML format)
        if use_history_compression and self._is_xml_content(content):
            preserve_tokens = config.get('history_preserve_tokens', 500)
            history_ratio = config.get('history_compression_ratio', 0.3)
            history_result = self._compress_sectional_history(processed_content, preserve_tokens, history_ratio)
            processed_content = history_result.get("compressed_content", processed_content)
        
        # 3. Execute main compression logic - if LLM client exists, use LLM compression; otherwise use simple compression
        if self.client:
            # Use LLM compression
            max_model_tokens = 8192  # Default model token limit
            try:
                result = self.compress_text(
                    processed_content, 
                    target_modules, 
                    max_model_tokens=max_model_tokens,
                    compression_ratio=compression_ratio,
                    output_format="xml"
                )
                compressed_content = result.get("compressed_content", processed_content)
                print(f"✅ LLM compression completed: {original_tokens} -> {self.count_tokens(compressed_content)} tokens")
            except Exception as e:
                print(f"⚠️ LLM compression failed: {e}, using fallback compression")
                compressed_content = self._compress_text_simple(
                    processed_content, target_modules, max_tokens, compression_ratio
                )
        else:
            # Use simple compression
            compressed_content = self._compress_text_simple(
                processed_content, target_modules, max_tokens, compression_ratio
            )
            print(f"✅ Simple compression completed: {original_tokens} -> {self.count_tokens(compressed_content)} tokens")
        
        return compressed_content
    
    def compress_text(self, 
                     content: str, 
                     target_modules: List[str], 
                     max_model_tokens: int = 8192,
                     compression_ratio: float = 0.3,
                     temperature: float = 0.1,
                     output_format: str = "xml") -> Dict[str, Any]:
        """
        Use LLM to compress multi-agent context into structured format (XML or Markdown)
        
        Args:
            content: Original context content (XML or markdown with sections)
            target_modules: List of sections to prioritize for compression
            max_model_tokens: Maximum model token limit (e.g., 8192 for GPT-4)
            compression_ratio: Target compression ratio (0.0-1.0, e.g., 0.3 = compress to 30%)
            temperature: Model creativity parameter
            output_format: Force specific output format ("xml" or "markdown")
            
        Returns:
            Dictionary containing structured output and compression statistics
        """
        if not self.client:
            raise Exception("LLM client not initialized")
            
        original_tokens = self.count_tokens(content)
        
        # Calculate target tokens based on max_model_tokens and compression_ratio
        target_tokens = int(original_tokens * compression_ratio)
        
        if original_tokens <= target_tokens:
            return {
                "compressed_content": content,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "compression_ratio": 1.0,
                "target_tokens": target_tokens,
                "max_model_tokens": max_model_tokens,
                "requested_compression_ratio": compression_ratio,
                "message": "Original content already meets target size, no compression needed"
            }
        
        prompt = self._create_compression_prompt(content, target_modules, target_tokens, output_format)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a context compression expert specialized in {output_format.upper()} format. Your job is to analyze multi-agent context data and generate structured {output_format.upper()} output within {target_tokens} tokens. Focus on extracting essential information while maintaining the {output_format} structure. Output ONLY the compressed {output_format} structure."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=min(target_tokens + 1000, 4096)  # Give some buffer space
            )
            
            compressed_content = response.choices[0].message.content.strip()
            compressed_tokens = self.count_tokens(compressed_content)
            compression_ratio_actual = 1 - compressed_tokens / original_tokens
            
            return {
                "compressed_content": compressed_content,
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "compression_ratio": compression_ratio_actual,
                "target_tokens": target_tokens,
                "max_model_tokens": max_model_tokens,
                "requested_compression_ratio": compression_ratio,
                "success": compressed_tokens <= target_tokens,
                "output_format": output_format,
                "message": f"Compression completed, from {original_tokens} to {compressed_tokens} tokens (target: {target_tokens}) in {output_format.upper()} format"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "original_tokens": original_tokens,
                "success": False,
                "message": f"Compression failed: {str(e)}"
            }

    def _create_compression_prompt(self, 
                                 content: str, 
                                 target_modules: List[str], 
                                 target_tokens: int,
                                 output_format: str) -> str:
        """Create XML compression prompt"""
        
        original_tokens = self.count_tokens(content)
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
                <!-- Knowledge base results compressed, system prompt preserved -->
                <system_prompt><!-- Keep original system prompt unchanged --></system_prompt>
                <task><!-- Preserve main task description --></task>
                <knowledge><!-- Compressed key facts and concepts --></knowledge>
                <external_knowledge><!-- Essential sources only --></external_knowledge>
            </BACKGROUND>

            <PLAN>
                <!-- Plans organized by iteration, remove intermediate processes -->
                <plan_iteration number="1">
                    <steps><!-- Key steps only --></steps>
                </plan_iteration>
            </PLAN>

            <SUB_APP>
                <!-- Summarize each agent's key contributions and results -->
                <agent name="xxxx">
                    <content><!-- Core findings, what was completed, results obtained --></content>
                </agent>
            </SUB_APP>

            <HISTORY>
                <!-- Compress conversation, extract critical information -->
                <entry role="system">
                    <!-- Compressed conversation summary -->
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

        **SUB_APP Section** ({"✓" if "SUB_APP" in target_modules else "○"} Priority):
        - Core findings, search results, key discoveries
        - Remove verbose API responses and metadata

        **HISTORY Section** ({"✓" if "HISTORY" in target_modules else "○"} Priority):
        - Extract main conversation topics and key decision points
        - Convert dialogue to essential entries only

        ## EXECUTION RULES

        1. **Token Priority**: Meeting ≤{target_tokens} tokens is MANDATORY
        2. **XML Structure**: Must follow exact XML format shown above
        3. **Compression Order**: Process priority sections more aggressively
        4. **Information Density**: Be ruthlessly concise while preserving key information
        5. **Complete Structure**: Include ALL four main sections in XML output

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
    
    def _is_xml_content(self, content: str) -> bool:
        """Check if content is XML format"""
        content_stripped = content.strip()
        xml_indicators = [
            content_stripped.startswith('<?xml'),
            content_stripped.startswith('<context>'),
            '<message' in content and 'role=' in content,
            bool(re.search(r'<[^>]+>[^<]*</[^>]+>', content))
        ]
        return any(xml_indicators)
    
    def _compress_text_by_tf_idf(self, content: str, target_ratio: float) -> str:
        """
        Use TF-IDF to compress text, mainly targeting SUB_APP section in XML format
        Reference implementation logic in compressor.py
        
        Args:
            content: XML content containing SUB_APP section
            target_ratio: Compression ratio (e.g., 0.6 means retain 60% of sentences)
        
        Returns:
            Compressed XML content with TF-IDF compressed SUB_APP section
        """
        import xml.etree.ElementTree as ET
        
        # Check if content is XML format
        if not self._is_xml_content(content):
            # For non-XML content, use TF-IDF compression directly
            try:
                result = self.tf_idf_compressor.compress_by_ratio(content, target_ratio)
                print(f"🔧 TF-IDF simple compression: {result.get('sentences_total', 0)} -> {result.get('sentences_kept', 0)} sentences")
                return result.get('compressed_text', content)
            except Exception as e:
                print(f"⚠️ TF-IDF compression failed: {e}")
                return content
        
        try:
            # Parse XML content
            # If content is not complete XML, wrap in context tag
            if not content.strip().startswith('<?xml') and not content.strip().startswith('<context>'):
                content = f"<context>\n{content}\n</context>"
                need_unwrap = True
            else:
                need_unwrap = False
            
            root = ET.fromstring(content)
            
            # Find SUB_APP section
            sub_app_element = root.find('.//SUB_APP')
            if sub_app_element is None:
                print("📝 SUB_APP section not found, skipping TF-IDF compression")
                return content
            
            total_agents_processed = 0
            total_sentences_before = 0
            total_sentences_after = 0
            
            # Process each agent in SUB_APP
            for agent_element in sub_app_element.findall('agent'):
                agent_name = agent_element.get('name', 'unknown')
                content_element = agent_element.find('content')
                
                if content_element is not None and content_element.text:
                    original_content = content_element.text.strip()
                    
                    if len(original_content) > 50:  # Only compress longer content
                        # Apply TF-IDF compression to agent content
                        try:
                            compression_result = self.tf_idf_compressor.compress_by_ratio(
                                original_content, target_ratio
                            )
                            
                            compressed_text = compression_result.get('compressed_text', original_content)
                            sentences_kept = compression_result.get('sentences_kept', 0)
                            sentences_total = compression_result.get('sentences_total', 0)
                            
                            # Update content element
                            content_element.text = compressed_text
                            
                            total_agents_processed += 1
                            total_sentences_before += sentences_total
                            total_sentences_after += sentences_kept
                            
                            print(f"🤖 Agent '{agent_name}': {sentences_total} -> {sentences_kept} sentences (compression ratio: {compression_result.get('compression_ratio', 0):.2%})")
                            
                        except Exception as e:
                            print(f"⚠️ Agent '{agent_name}' TF-IDF compression failed: {e}")
                    else:
                        print(f"📝 Agent '{agent_name}': Content too short, skipping compression")
            
            if total_agents_processed > 0:
                print(f"✅ TF-IDF compression completed: Processed {total_agents_processed} Agents, total sentences {total_sentences_before} -> {total_sentences_after}")
            
            # Convert modified XML back to string
            compressed_xml = ET.tostring(root, encoding='unicode', method='xml')
            
            # If original content was not wrapped in <context>, remove wrapper
            if need_unwrap:
                import re
                compressed_xml = re.sub(r'^<context>\s*', '', compressed_xml)
                compressed_xml = re.sub(r'\s*</context>$', '', compressed_xml)
            
            return compressed_xml
            
        except ET.ParseError as e:
            print(f"⚠️ XML parsing failed, trying regex method: {e}")
            return self._compress_subapp_by_regex(content, target_ratio)
        except Exception as e:
            print(f"⚠️ TF-IDF XML compression failed: {e}")
            return content
    
    def _compress_subapp_by_regex(self, content: str, target_ratio: float) -> str:
        """
        Fallback method: Use regex to compress SUB_APP content when XML parsing fails
        
        Args:
            content: Original content
            target_ratio: TF-IDF compression ratio
            
        Returns:
            Content with compressed SUB_APP section
        """
        import re
        
        # Find SUB_APP section
        sub_app_pattern = r'<SUB_APP>(.*?)</SUB_APP>'
        sub_app_match = re.search(sub_app_pattern, content, re.DOTALL)
        
        if not sub_app_match:
            print("📝 Regex method: SUB_APP section not found")
            return content
        
        sub_app_content = sub_app_match.group(1)
        
        # Find all agent sections
        agent_pattern = r'<agent\s+name="([^"]*)"[^>]*>\s*<content>(.*?)</content>\s*</agent>'
        agent_matches = re.findall(agent_pattern, sub_app_content, re.DOTALL)
        
        if not agent_matches:
            print("📝 Regex method: No agent content found")
            return content
        
        compressed_agents = []
        total_agents_processed = 0
        
        for agent_name, agent_content in agent_matches:
            agent_content = agent_content.strip()
            
            if len(agent_content) > 50:  # Only compress longer content
                try:
                    compression_result = self.tf_idf_compressor.compress_by_ratio(
                        agent_content, target_ratio
                    )
                    
                    compressed_text = compression_result.get('compressed_text', agent_content)
                    sentences_kept = compression_result.get('sentences_kept', 0)
                    sentences_total = compression_result.get('sentences_total', 0)
                    
                    print(f"🤖 Agent '{agent_name}' (regex): {sentences_total} -> {sentences_kept} sentences")
                    total_agents_processed += 1
                    
                    compressed_agents.append(f'<agent name="{agent_name}"><content>{compressed_text}</content></agent>')
                    
                except Exception as e:
                    print(f"⚠️ Agent '{agent_name}' TF-IDF compression failed: {e}")
                    compressed_agents.append(f'<agent name="{agent_name}"><content>{agent_content}</content></agent>')
            else:
                compressed_agents.append(f'<agent name="{agent_name}"><content>{agent_content}</content></agent>')
        
        # Rebuild SUB_APP section
        new_sub_app_content = f"<SUB_APP>\n{chr(10).join(compressed_agents)}\n</SUB_APP>"
        
        # Replace original SUB_APP section
        result = re.sub(sub_app_pattern, new_sub_app_content, content, flags=re.DOTALL)
        
        print(f"✅ Regex method TF-IDF compression completed: Processed {total_agents_processed} Agents")
        
        return result
    
    def _compress_sectional_history(self, content: str, preserve_last_tokens: int = 500, compression_ratio: float = 0.3) -> Dict[str, Any]:
        """
        Compress sectional conversation history, preserve recent conversations, compress older history
        Supports both XML format and JSON array format
        Implements according to compress_sectional_history in compressor.py
        
        Args:
            content: Content to compress
            preserve_last_tokens: Number of latest tokens to preserve (default 500)
            compression_ratio: History content compression ratio, 0.3 means compress to 30% (default 0.3)
        """
        max_model_tokens = 8192
        temperature = 0.1
        
        # Check if content is XML format and contains HISTORY section
        if self._is_xml_content(content) and '<HISTORY>' in content:
            return self._compress_xml_history(content, preserve_last_tokens, compression_ratio, max_model_tokens, temperature)
        else:
            # Process as JSON array format (original implementation)
            return self._compress_json_history(content, preserve_last_tokens, compression_ratio, max_model_tokens, temperature)
    
    def _compress_xml_history(self, 
                             xml_content: str,
                             preserve_last_tokens: int,
                             compression_ratio: float,
                             max_model_tokens: int,
                             temperature: float) -> Dict[str, Any]:
        """Compress XML format history content"""
        # Extract HISTORY section
        history_start = xml_content.find('<HISTORY>')
        history_end = xml_content.find('</HISTORY>') + len('</HISTORY>')
        
        if history_start == -1 or history_end == -1:
            return {"compressed_content": xml_content, "message": "No HISTORY section found"}
        
        history_content = xml_content[history_start:history_end]
        xml_without_history = xml_content[:history_start] + xml_content[history_end:]
        
        # Extract all entry elements
        import re
        entry_pattern = r'<entry[^>]*role="([^"]*)"[^>]*>(.*?)</entry>'
        entries = re.findall(entry_pattern, history_content, re.DOTALL)
        
        if not entries:
            return {"compressed_content": xml_content, "message": "No entries found in HISTORY section"}
        
        # Convert to JSON format for processing
        history_array = [{"role": role, "message": message.strip()} for role, message in entries]
        
        # Use existing JSON compression logic
        import json
        history_json_str = json.dumps(history_array, ensure_ascii=False)
        
        compression_result = self._compress_json_history(
            history_json_str, preserve_last_tokens, compression_ratio, max_model_tokens, temperature
        )
        
        if compression_result.get("success", True):
            # 解析压缩后的 JSON 并重建 XML
            compressed_history_str = compression_result["compressed_content"]
            
            try:
                if not compressed_history_str.strip().startswith('['):
                    compressed_history_str = '[' + compressed_history_str + ']'
                compressed_history_array = json.loads(compressed_history_str)
            except json.JSONDecodeError:
                compressed_history_array = history_array
            
            # 重建 HISTORY 部分
            new_history_entries = []
            for item in compressed_history_array:
                role = item.get('role', 'system')
                message = item.get('message', '')
                new_history_entries.append(f'        <entry role="{role}">{message}</entry>')
            
            new_history_section = f"<HISTORY>\n{chr(10).join(new_history_entries)}\n    </HISTORY>"
            
            # 插入压缩后的历史部分
            final_xml = xml_without_history.replace('</context>', f"    {new_history_section}\n</context>")
            
            compression_result["compressed_content"] = final_xml
            compression_result["compressed_tokens"] = self.count_tokens(final_xml)
            compression_result["original_tokens"] = self.count_tokens(xml_content)
            
        return compression_result
    
    def _compress_json_history(self, 
                              sectional_content: str,
                              preserve_last_tokens: int,
                              compression_ratio: float,
                              max_model_tokens: int,
                              temperature: float) -> Dict[str, Any]:
        """Original JSON array format compression logic"""
        import json
        
        original_tokens = self.count_tokens(sectional_content)
        
        # If original content doesn't exceed preservation threshold, return as is
        if original_tokens <= preserve_last_tokens:
            return {
                "compressed_content": sectional_content,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "compression_ratio": 1.0,
                "preserve_last_tokens": preserve_last_tokens,
                "message": "Content does not exceed preservation threshold, no compression needed"
            }
        
        # Split content: parts to compress + parts to preserve
        try:
            data = json.loads(sectional_content)
            if not isinstance(data, list):
                return {"compressed_content": sectional_content, "message": "Invalid JSON array format"}
        except json.JSONDecodeError:
            return {"compressed_content": sectional_content, "message": "Failed to parse JSON"}
        
        # Calculate how many items to preserve - consider role relationships, split at user messages
        total_items = len(data)
        preserve_tokens_used = 0
        preserve_items = 0
        
        # Step 1: Calculate approximate split point from back to front
        for i in range(total_items - 1, -1, -1):
            item_str = json.dumps(data[i], ensure_ascii=False)
            item_tokens = self.count_tokens(item_str)
            if preserve_tokens_used + item_tokens <= preserve_last_tokens:
                preserve_tokens_used += item_tokens
                preserve_items += 1
            else:
                break
        
        # Step 2: Find appropriate user split point
        tentative_split_index = total_items - preserve_items
        
        # From estimated split point, look forward for first user message as actual split point
        final_split_index = tentative_split_index
        for i in range(tentative_split_index, total_items):
            try:
                if isinstance(data[i], dict) and data[i].get('role') == 'user':
                    final_split_index = i
                    break
            except (TypeError, AttributeError):
                continue
        
        # If no user message found, try looking backward
        if final_split_index == tentative_split_index and tentative_split_index > 0:
            for i in range(tentative_split_index - 1, -1, -1):
                try:
                    if isinstance(data[i], dict) and data[i].get('role') == 'user':
                        final_split_index = i
                        break
                except (TypeError, AttributeError):
                    continue
        
        # Split data - using found user split point
        items_to_compress = data[:final_split_index]
        items_to_preserve = data[final_split_index:]
        
        print(f"🔍 Split info: Total={total_items}, Estimated split={tentative_split_index}, Final split={final_split_index}")
        print(f"📦 Items to compress={len(items_to_compress)}, Items to preserve={len(items_to_preserve)}")
        
        # Verify first preserved item is a user message
        if items_to_preserve and isinstance(items_to_preserve[0], dict):
            first_preserved_role = items_to_preserve[0].get('role', 'unknown')
            print(f"👤 First preserved message role: {first_preserved_role}")
        
        if not items_to_compress:
            return {
                "compressed_content": sectional_content,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "compression_ratio": 1.0,
                "message": "No items to compress"
            }
        
        # Compress parts that need compression
        content_to_compress = json.dumps(items_to_compress, ensure_ascii=False)
        compress_tokens = self.count_tokens(content_to_compress)
        target_tokens = int(compress_tokens * compression_ratio)
        
        # If no LLM client, use simple compression
        if not self.client:
            # Simply keep first few items
            keep_items = max(1, int(len(items_to_compress) * compression_ratio))
            compressed_items = items_to_compress[:keep_items]
        else:
            # Use LLM compression
            try:
                prompt = self._create_sectional_compression_prompt(content_to_compress, target_tokens)
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are a compression expert specializing in sectional dialogue history. Your task is to compress lengthy dialogue history into concise key point summaries while preserving key information and decision processes."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=min(target_tokens + 500, max_model_tokens)
                )
                
                compressed_history = response.choices[0].message.content.strip()
                compressed_items = [{"role": "system", "message": compressed_history}]
                
            except Exception as e:
                print(f"LLM compression failed: {e}, using simple compression")
                keep_items = max(1, int(len(items_to_compress) * compression_ratio))
                compressed_items = items_to_compress[:keep_items]
        
        # Merge compressed content with preserved content
        final_items = compressed_items + items_to_preserve
        final_content = json.dumps(final_items, ensure_ascii=False)
        final_tokens = self.count_tokens(final_content)
        final_compression_ratio = 1 - final_tokens / original_tokens
        
        return {
            "compressed_content": final_content,
            "original_tokens": original_tokens,
            "compressed_tokens": final_tokens,
            "compression_ratio": final_compression_ratio,
            "preserve_last_tokens": preserve_last_tokens,
            "success": True,
            "message": f"Section compression completed: {original_tokens} → {final_tokens} tokens"
        }
    
    def _create_sectional_compression_prompt(self, content_to_compress: str, target_tokens: int) -> str:
        """Create sectional compression prompt"""
        original_tokens = self.count_tokens(content_to_compress)
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
    
    def _compress_text_simple(self, content: str, target_modules: List[str], max_tokens: int, compression_ratio: float) -> str:
        """
        Simplified version of text compression, mimicking core logic of compress_text
        
        Args:
            content: Content to compress
            target_modules: Target modules (section information)
            max_tokens: Maximum token count
            compression_ratio: Compression ratio
            
        Returns:
            Compressed content
        """
        current_tokens = self.count_tokens(content)
        
        if current_tokens <= max_tokens:
            return content
        
                    # Split content by lines
            lines = content.split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            # Classify: important lines (to keep) and normal lines (compressible)
            important_lines = []
            compressible_lines = []
            
            for line in lines:
                # Check if line contains keywords from target_modules
                is_target = any(module.upper() in line.upper() for module in target_modules) if target_modules and 'all' not in target_modules else False
                
                # Check if line is structurally important (XML tags, system prompts, etc.)
                is_structural = any([
                    line.startswith('<') and line.endswith('>'),
                    'role=' in line,
                    line.startswith('<?xml'),
                    len(line) < 50  # Short lines are usually important
                ])
                
                if is_structural or not is_target:
                    important_lines.append(line)
                else:
                    compressible_lines.append(line)
            
            # Build result: first add important lines
            result_lines = important_lines.copy()
            current_tokens = self.count_tokens('\n'.join(result_lines))
            
            # Add compressible lines as needed, sorted by length
            compressible_lines.sort(key=len, reverse=True)
            
            for line in compressible_lines:
                line_tokens = self.count_tokens(line)
                if current_tokens + line_tokens <= max_tokens:
                    result_lines.append(line)
                    current_tokens += line_tokens
                else:
                    break
            
            compressed_result = '\n'.join(result_lines)
            
            # If still too long, truncate
            if self.count_tokens(compressed_result) > max_tokens:
                # Simple truncation to appropriate length
                chars_per_token = len(compressed_result) / self.count_tokens(compressed_result)
                target_chars = int(max_tokens * chars_per_token * 0.9)  # Leave some margin
                compressed_result = compressed_result[:target_chars]
        
        return compressed_result