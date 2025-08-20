import React, { useState, useCallback, useEffect } from 'react';
import { apiService, CompressionRequest, CompressionResponse } from '../services/api';
import { AlertCircle, Settings, Play, FileText, Zap, Key, Info, Save, Check } from 'lucide-react';

interface CompressorProps {}

// API configuration interface
interface ApiConfig {
  openai_api_key: string;
  openai_base_url: string;
}

const Compressor: React.FC<CompressorProps> = () => {
  // API configuration state (set once, persistent)
  const [apiConfig, setApiConfig] = useState<ApiConfig>({
    openai_api_key: '',
    openai_base_url: 'https://oneapi.fastgpt.in/v1'
  });
  
  const [isApiConfigured, setIsApiConfigured] = useState(false);
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [apiConfigSaved, setApiConfigSaved] = useState(false);

  const [formData, setFormData] = useState<CompressionRequest>({
    role: 'system',
    section: 'BACKGROUND',
    content: '',
    target_modules: ['all'],
    use_tf_idf: false,
    use_history_compression: false,
    max_token: 1000,
    
    // TF-IDF compression parameter default values
    tf_idf_compression_ratio: 0.6, // Retain 60% of sentences
    
    // History compression parameter default values
    history_preserve_tokens: 500, // Preserve latest 500 tokens
    history_compression_ratio: 0.3, // Compress to 30%
    
    openai_api_key: '',
    openai_base_url: ''
  });

  const [result, setResult] = useState<CompressionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Structured data state
  const [structuredData, setStructuredData] = useState({
    // BACKGROUND section data
    background: {
      system_prompt: '',
      task: '',
      knowledge: '',
      external_knowledge: ''
    },
    // PLAN section data
    plan: {
      steps: [''],
      call_ask: ''
    },
    // SUB_APP section data
    subapp: {
      app_name: '',
      content: ''
    }
  });

  // Load API configuration from localStorage
  useEffect(() => {
    const savedConfig = localStorage.getItem('context-compressor-api-config');
    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig);
        setApiConfig(parsed);
        setIsApiConfigured(!!parsed.openai_api_key);
        setApiConfigSaved(true);
      } catch (error) {
        console.error('Failed to parse saved API config:', error);
      }
    }
  }, []);

  // Save API configuration to localStorage
  const saveApiConfig = () => {
    if (!apiConfig.openai_api_key.trim()) {
              setError('Please enter API Key');
      return;
    }

    localStorage.setItem('context-compressor-api-config', JSON.stringify(apiConfig));
    setIsApiConfigured(true);
    setApiConfigSaved(true);
    setShowApiConfig(false);
    setError('');
    
    // Show save success message
    setTimeout(() => setApiConfigSaved(false), 3000);
  };

  // Clear API configuration
  const clearApiConfig = () => {
    localStorage.removeItem('context-compressor-api-config');
    setApiConfig({
      openai_api_key: '',
      openai_base_url: 'https://oneapi.fastgpt.in/v1'
    });
    setIsApiConfigured(false);
    setApiConfigSaved(false);
  };

  const handleInputChange = useCallback((field: keyof CompressionRequest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleStructuredDataChange = useCallback((section: string, field: string, value: any) => {
    setStructuredData(prev => ({
      ...prev,
      [section]: {
        ...prev[section as keyof typeof prev],
        [field]: value
      }
    }));
  }, []);

  const addPlanStep = useCallback(() => {
    setStructuredData(prev => ({
      ...prev,
      plan: {
        ...prev.plan,
        steps: [...prev.plan.steps, '']
      }
    }));
  }, []);

  const removePlanStep = useCallback((index: number) => {
    setStructuredData(prev => ({
      ...prev,
      plan: {
        ...prev.plan,
        steps: prev.plan.steps.filter((_, i) => i !== index)
      }
    }));
  }, []);

  const updatePlanStep = useCallback((index: number, value: string) => {
    setStructuredData(prev => ({
      ...prev,
      plan: {
        ...prev.plan,
        steps: prev.plan.steps.map((step, i) => i === index ? value : step)
      }
    }));
  }, []);

  const handleApiConfigChange = useCallback((field: keyof ApiConfig, value: string) => {
    setApiConfig(prev => ({ ...prev, [field]: value }));
    setApiConfigSaved(false);
  }, []);

  const handleCompress = async () => {
    // Build content based on section type
    let content = '';
    
    if (formData.section === 'BACKGROUND') {
      // Build BACKGROUND JSON structure
      const bg = structuredData.background;
      if (!bg.system_prompt.trim()) {
        setError('Please fill in System Prompt');
        return;
      }
      content = JSON.stringify({
        system_prompt: bg.system_prompt,
        task: bg.task,
        knowledge: bg.knowledge,
        external_knowledge: bg.external_knowledge
      });
    } else if (formData.section === 'PLAN') {
      // Build PLAN structure
      const plan = structuredData.plan;
      const validSteps = plan.steps.filter(step => step.trim() !== '');
      if (validSteps.length === 0) {
        setError('Please add at least one plan step');
        return;
      }
      content = JSON.stringify({
        steps: validSteps,
        call_ask: plan.call_ask
      });
    } else if (formData.section === 'SUB_APP') {
      // Build SUB_APP structure
      const subapp = structuredData.subapp;
      if (!subapp.app_name.trim() || !subapp.content.trim()) {
        setError('Please fill in app name and content');
        return;
      }
      content = JSON.stringify({
        app_name: subapp.app_name,
        content: subapp.content
      });
    } else {
      // HISTORY section uses original content field
      content = formData.content;
      if (!content.trim()) {
        setError('Please enter historical conversation content');
        return;
      }
    }

    setLoading(true);
    setError('');
    
    try {
      // Use saved API configuration
      const requestData = {
        ...formData,
        content, // Use built content
        openai_api_key: apiConfig.openai_api_key,
        openai_base_url: apiConfig.openai_base_url
      };
      
      const response = await apiService.compressContext(requestData);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Compression failed');
    } finally {
      setLoading(false);
    }
  };

  const formatXML = (xmlString: string): string => {
    return xmlString;
  };

  // Generate real-time preview XML content
  const generatePreviewXML = (): string => {
    if (formData.section === 'BACKGROUND') {
      const bg = structuredData.background;
      return `<context>
  <BACKGROUND>
    <system_prompt>
      ${bg.system_prompt || 'System prompt...'}
    </system_prompt>
    <task>
      ${bg.task || 'Task description...'}
    </task>
    <knowledge>
      ${bg.knowledge || 'Knowledge base content...'}
    </knowledge>
    <external_knowledge>
      ${bg.external_knowledge || 'External knowledge...'}
    </external_knowledge>
  </BACKGROUND>
</context>`;
    } else if (formData.section === 'PLAN') {
      const plan = structuredData.plan;
      const stepsXml = plan.steps.filter(s => s.trim()).map((step, i) => `        <step>${step}</step>`).join('\n');
      return `<context>
  <PLAN>
    <plan_iteration number="1">
      <steps>
      ${stepsXml || '        <step>Plan step...</step>'}
      </steps>
    </plan_iteration>
    ${plan.call_ask ? `<call_ask>${plan.call_ask}</call_ask>` : ''}
  </PLAN>
</context>`;
    } else if (formData.section === 'SUB_APP') {
      const subapp = structuredData.subapp;
      return `<context>
  <SUB_APP>
    <agent name="${subapp.app_name || 'AppName'}">
      <content>
        ${subapp.content || 'App content...'}
      </content>
    </agent>
  </SUB_APP>
</context>`;
    } else if (formData.section === 'HISTORY') {
      return `<context>
  <HISTORY>
    <entry role="${formData.role}">
      ${formData.content || 'Conversation content...'}
    </entry>
  </HISTORY>
</context>`;
    }
    return '';
  };

  // Get section description
  const getSectionDescription = (section: string): string => {
    const descriptions = {
      'BACKGROUND': 'Background information - Contains system prompts, task descriptions, knowledge base and other basic information',
      'PLAN': 'Planning - Contains task plans, step arrangements, iteration information, etc.',
      'SUB_APP': 'Sub-applications - Contains execution results, discoveries and contributions from various agents',
      'HISTORY': 'Historical conversations - Contains conversation history, message records, etc., supports role settings'
    };
    return descriptions[section as keyof typeof descriptions] || '';
  };

  // Check if in HISTORY section
  const isHistorySection = formData.section === 'HISTORY';

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
              {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <Zap className="h-8 w-8 text-blue-400" />
              <h1 className="text-xl font-bold text-white">Context Compression System</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-400">Intelligent LLM Compression | Hierarchical Structure</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upper part: Input area and real-time preview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Left: Input area */}
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center">
                <Settings className="mr-2 h-5 w-5" />
                Configuration Parameters
              </h2>
              
              {/* Section selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Section Type</label>
                <select
                  value={formData.section}
                  onChange={(e) => handleInputChange('section', e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="BACKGROUND">BACKGROUND</option>
                  <option value="PLAN">PLAN</option>
                  <option value="SUB_APP">SUB APP</option>
                  <option value="HISTORY">HISTORY</option>
                </select>
                <div className="mt-2 text-xs text-gray-400 flex items-start">
                  <Info className="mr-1 h-3 w-3 mt-0.5 flex-shrink-0" />
                  <span>{getSectionDescription(formData.section)}</span>
                </div>
              </div>

              {/* API Configuration */}
              <div className="mb-4">
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => setShowApiConfig(!showApiConfig)}
                    className={`flex items-center text-sm ${isApiConfigured ? 'text-green-400 hover:text-green-300' : 'text-yellow-400 hover:text-yellow-300'}`}
                  >
                    <Key className="mr-1 h-4 w-4" />
                    OpenAI API Configuration {showApiConfig ? '▼' : '▶'}
                    {isApiConfigured && <Check className="ml-2 h-4 w-4" />}
                  </button>
                  {apiConfigSaved && (
                    <span className="text-green-400 text-xs flex items-center">
                      <Check className="mr-1 h-3 w-3" />
                      Saved
                    </span>
                  )}
                </div>
                {isApiConfigured && (
                  <div className="mt-2 text-xs text-green-300">
                    ✅ API configured, will use intelligent LLM compression
                  </div>
                )}
              </div>

              {showApiConfig && (
                <div className="space-y-4 p-4 bg-gray-750 rounded-lg border border-green-600 mb-6">
                  <div className="text-xs text-green-300 mb-3">
                    <Info className="inline mr-1 h-3 w-3" />
                    Configure once, persistent storage. Will automatically use intelligent LLM compression after configuration
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">API Key *</label>
                    <input
                      type="password"
                      value={apiConfig.openai_api_key}
                      onChange={(e) => handleApiConfigChange('openai_api_key', e.target.value)}
                      placeholder="Enter your OpenAI API Key"
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Base URL</label>
                    <input
                      type="text"
                      value={apiConfig.openai_base_url}
                      onChange={(e) => handleApiConfigChange('openai_base_url', e.target.value)}
                      placeholder="https://oneapi.fastgpt.in/v1"
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={saveApiConfig}
                      disabled={!apiConfig.openai_api_key.trim()}
                      className="flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-md font-medium transition-colors text-sm"
                    >
                      <Save className="mr-1 h-4 w-4" />
                      Save Configuration
                    </button>
                    {isApiConfigured && (
                      <button
                        onClick={clearApiConfig}
                        className="flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 rounded-md font-medium transition-colors text-sm"
                      >
                        Clear Configuration
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Advanced configuration */}
              <div className="mb-4">
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center text-blue-400 hover:text-blue-300 text-sm"
                >
                  <Settings className="mr-1 h-4 w-4" />
                  Advanced Parameters {showAdvanced ? '▼' : '▶'}
                </button>
              </div>

              {showAdvanced && (
                <div className="space-y-4 p-4 bg-gray-750 rounded-lg border border-gray-600">
                  <div>
                    <label className="block text-sm font-medium mb-2">Maximum Token Count</label>
                    <input
                      type="number"
                      value={formData.max_token}
                      onChange={(e) => handleInputChange('max_token', e.target.value === '' ? '' : parseInt(e.target.value))}
                      onBlur={(e) => {
                        if (e.target.value === '' || isNaN(parseInt(e.target.value))) {
                          handleInputChange('max_token', 1000);
                        }
                      }}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:ring-2 focus:ring-blue-500"
                      min="100"
                      max="10000"
                      placeholder="1000"
                    />
                    <div className="text-xs text-yellow-200 mt-1">
                        1000 is for test, please set a larger value for production use
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.use_tf_idf}
                        onChange={(e) => handleInputChange('use_tf_idf', e.target.checked)}
                        className="mr-2 rounded bg-gray-700 border-gray-600 text-blue-600"
                      />
                      <span className="text-sm">Enable TF-IDF preprocessing (for Sub App section)</span>
                    </label>
                    
                    {/* TF-IDF parameter configuration */}
                    {formData.use_tf_idf && (
                      <div className="ml-6 space-y-3 p-3 bg-gray-800 rounded border border-blue-500">
                        <div>
                          <label className="block text-xs font-medium mb-1 text-blue-300">TF-IDF retention ratio (sentence retention rate)</label>
                          <input
                            type="number"
                            value={formData.tf_idf_compression_ratio}
                            onChange={(e) => handleInputChange('tf_idf_compression_ratio', e.target.value === '' ? '' : parseFloat(e.target.value))}
                            onBlur={(e) => {
                              if (e.target.value === '' || isNaN(parseFloat(e.target.value))) {
                                handleInputChange('tf_idf_compression_ratio', 0.6);
                              }
                            }}
                            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                            min="0.1"
                            max="1.0"
                            step="0.1"
                            placeholder="0.6"
                          />
                          <div className="text-xs text-blue-300 mt-1">
                            0.6 = retain 60% of important sentences, higher value retains more content
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.use_history_compression}
                        onChange={(e) => handleInputChange('use_history_compression', e.target.checked)}
                        className="mr-2 rounded bg-gray-700 border-gray-600 text-blue-600"
                      />
                      <span className="text-sm">History compression optimization (for History section)</span>
                    </label>
                    
                    {/* History compression parameter configuration */}
                    {formData.use_history_compression && (
                      <div className="ml-6 space-y-3 p-3 bg-gray-800 rounded border border-green-500">
                        <div>
                          <label className="block text-xs font-medium mb-1 text-green-300">Preserve latest token count</label>
                          <input
                            type="number"
                            value={formData.history_preserve_tokens}
                            onChange={(e) => handleInputChange('history_preserve_tokens', e.target.value === '' ? '' : parseInt(e.target.value))}
                            onBlur={(e) => {
                              if (e.target.value === '' || isNaN(parseInt(e.target.value))) {
                                handleInputChange('history_preserve_tokens', 500);
                              }
                            }}
                            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                            min="100"
                            max="2000"
                            step="50"
                            placeholder="500"
                          />
                          <div className="text-xs text-green-300 mt-1">
                            Preserve the latest token count in conversation history, default 500
                          </div>
                        </div>
                        <div>
                          <label className="block text-xs font-medium mb-1 text-green-300">History content compression ratio</label>
                          <input
                            type="number"
                            value={formData.history_compression_ratio}
                            onChange={(e) => handleInputChange('history_compression_ratio', e.target.value === '' ? '' : parseFloat(e.target.value))}
                            onBlur={(e) => {
                              if (e.target.value === '' || isNaN(parseFloat(e.target.value))) {
                                handleInputChange('history_compression_ratio', 0.3);
                              }
                            }}
                            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                            min="0.1"
                            max="1.0"
                            step="0.1"
                            placeholder="0.3"
                          />
                          <div className="text-xs text-green-300 mt-1">
                            0.3 = compress old conversations to 30%, lower value means more compression
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Structured input area */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                {formData.section} Section Content Input
              </h2>
              
              {/* BACKGROUND section structured input */}
              {formData.section === 'BACKGROUND' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-blue-300">System Prompt *</label>
                    <textarea
                      value={structuredData.background.system_prompt}
                      onChange={(e) => handleStructuredDataChange('background', 'system_prompt', e.target.value)}
                      placeholder="System prompt content..."
                      className="w-full h-20 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white resize-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-blue-300">Task</label>
                    <textarea
                      value={structuredData.background.task}
                      onChange={(e) => handleStructuredDataChange('background', 'task', e.target.value)}
                      placeholder="Task description..."
                      className="w-full h-20 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white resize-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-blue-300">Knowledge</label>
                    <textarea
                      value={structuredData.background.knowledge}
                      onChange={(e) => handleStructuredDataChange('background', 'knowledge', e.target.value)}
                      placeholder="Knowledge base content..."
                      className="w-full h-20 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white resize-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-blue-300">External Knowledge</label>
                    <textarea
                      value={structuredData.background.external_knowledge}
                      onChange={(e) => handleStructuredDataChange('background', 'external_knowledge', e.target.value)}
                      placeholder="External knowledge sources..."
                      className="w-full h-20 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white resize-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              )}
              
              {/* PLAN section structured input */}
              {formData.section === 'PLAN' && (
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-green-300">Plan Steps *</label>
                      <button
                        type="button"
                        onClick={addPlanStep}
                        className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors"
                      >
                        + Add Step
                      </button>
                    </div>
                    <div className="space-y-2">
                      {structuredData.plan.steps.map((step, index) => (
                        <div key={index} className="flex items-center space-x-2">
                          <span className="text-green-400 text-sm min-w-[60px]">Step {index + 1}:</span>
                          <input
                            type="text"
                            value={step}
                            onChange={(e) => updatePlanStep(index, e.target.value)}
                            placeholder={`Step ${index + 1} operation...`}
                            className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:ring-2 focus:ring-green-500"
                          />
                          {structuredData.plan.steps.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removePlanStep(index)}
                              className="px-2 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
                            >
                              ✖
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-green-300">Call Ask (Interaction Request)</label>
                    <textarea
                      value={structuredData.plan.call_ask}
                      onChange={(e) => handleStructuredDataChange('plan', 'call_ask', e.target.value)}
                      placeholder="Interaction requests or questions in the plan..."
                      className="w-full h-20 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white resize-none focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                </div>
              )}
              
              {/* SUB_APP section structured input */}
              {formData.section === 'SUB_APP' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-purple-300">App Name *</label>
                    <input
                      type="text"
                      value={structuredData.subapp.app_name}
                      onChange={(e) => handleStructuredDataChange('subapp', 'app_name', e.target.value)}
                      placeholder="App name, e.g., SearchAgent, AnalysisAgent..."
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-purple-300">Content *</label>
                    <textarea
                      value={structuredData.subapp.content}
                      onChange={(e) => handleStructuredDataChange('subapp', 'content', e.target.value)}
                      placeholder="App execution results, findings and contributions..."
                      className="w-full h-32 px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white resize-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>
              )}
              
              {/* HISTORY section structured input */}
              {formData.section === 'HISTORY' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-orange-300">Message Role</label>
                    <select
                      value={formData.role}
                      onChange={(e) => handleInputChange('role', e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:ring-2 focus:ring-orange-500"
                    >
                      <option value="system">System</option>
                      <option value="user">User</option>
                      <option value="assistant">Assistant</option>
                      <option value="tool">Tool</option>
                    </select>
                    <div className="mt-1 text-xs text-orange-300">
                      Select the role type for this historical message
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-orange-300">Message Content *</label>
                    <textarea
                      value={formData.content}
                      onChange={(e) => handleInputChange('content', e.target.value)}
                      placeholder="Enter your historical conversation content..."
                      className="w-full h-32 px-4 py-3 bg-gray-700 border border-gray-600 rounded-md text-white resize-none focus:ring-2 focus:ring-orange-500"
                    />
                  </div>
                </div>
              )}
              
              <div className="mt-4 flex justify-between items-center">
                <div className="text-sm text-gray-400">
                  Current Section: {formData.section} {formData.section === 'HISTORY' && `(Role: ${formData.role})`}
                </div>
                <button
                  onClick={handleCompress}
                  disabled={loading}
                  className="flex items-center px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-md font-medium transition-colors"
                >
                  <Play className="mr-2 h-4 w-4" />
                  {loading ? 'Compressing...' : 'Start Compression'}
                </button>
              </div>
            </div>
          </div>

          {/* Right side: Real-time preview area */}
          <div className="space-y-6">
            {error && (
              <div className="bg-red-800 border border-red-600 rounded-lg p-4 flex items-start">
                <AlertCircle className="mr-2 h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="text-red-200">{error}</div>
              </div>
            )}
            
            <div className="bg-gray-800 rounded-lg p-5">
              <h2 className="text-lg font-semibold mb-4 flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                Real-Time XML Preview
              </h2>
              <div className="bg-gray-900 p-4 rounded border border-gray-600 h-96 overflow-auto">
                {generatePreviewXML() ? (
                  <pre className="text-xs text-blue-200 whitespace-pre-wrap">
                    {generatePreviewXML()}
                  </pre>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <div className="text-center">
                      <FileText className="mx-auto h-8 w-8 mb-2" />
                      <p>Start filling in {formData.section} section content to view XML preview</p>
                    </div>
                  </div>
                )}
              </div>
              <div className="mt-4 text-sm text-gray-400 space-y-1">
                <div className="flex items-center">
                  <span className="w-2 h-2 bg-blue-400 rounded-full mr-2"></span>
                  <span>XML Format Preview - Shows pre-compression structure</span>
                </div>
                <div className="flex items-center">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                  <span>Current Section: {formData.section} {isHistorySection && `(Role: ${formData.role})`}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom part: Compression comparison results (only shown when results exist) */}
        {result && (
          <div className="space-y-6">
            {/* Compression statistics */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <Zap className="mr-2 h-5 w-5" />
                Compression Statistics
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-700 p-4 rounded text-center">
                  <div className="text-2xl font-bold text-blue-400">{(result.compression_ratio * 100).toFixed(1)}%</div>
                  <div className="text-sm text-gray-300">Compression Ratio</div>
                </div>
                <div className="bg-gray-700 p-4 rounded text-center">
                  <div className="text-2xl font-bold text-green-400">
                    {result.token_count_original - result.token_count_compressed}
                  </div>
                  <div className="text-sm text-gray-300">Tokens Saved</div>
                </div>
                <div className="bg-gray-700 p-4 rounded text-center">
                  <div className="text-2xl font-bold text-yellow-400">
                    {result.token_count_original} → {result.token_count_compressed}
                  </div>
                  <div className="text-sm text-gray-300">Token Change</div>
                </div>
              </div>
              <div className="mt-4 text-center text-sm text-gray-400">
                {result.message}
              </div>
            </div>

            {/* Before and after compression comparison */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-6 text-center">Before and After Compression Comparison</h3>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Before compression */}
                <div>
                  <h4 className="font-medium mb-3 text-gray-300 flex items-center">
                    <span className="w-3 h-3 bg-red-400 rounded-full mr-2"></span>
                    Before Compression ({result.token_count_original} tokens)
                  </h4>
                  <div className="bg-gray-900 p-4 rounded border border-gray-600 h-80 overflow-auto">
                    <pre className="text-xs text-gray-200 whitespace-pre-wrap">
                      {formatXML(result.original_content)}
                    </pre>
                  </div>
                </div>
                
                {/* After compression */}
                <div>
                  <h4 className="font-medium mb-3 text-gray-300 flex items-center">
                    <span className="w-3 h-3 bg-green-400 rounded-full mr-2"></span>
                    After Compression ({result.token_count_compressed} tokens)
                  </h4>
                  <div className="bg-gray-900 p-4 rounded border border-green-600 h-80 overflow-auto">
                    <pre className="text-xs text-green-200 whitespace-pre-wrap">
                      {formatXML(result.compressed_content)}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Compressor;