import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Upload, 
  FileText, 
  Plus, 
  X,
  AlertCircle,
  CheckCircle,
  Loader2,
  Trash2,
  Globe,
  Monitor
} from 'lucide-react';
import { CustomDropdown } from '../../shared/components/CustomDropdown';
import { useProjects } from '../../shared/hooks/useProjects';
import { BrowserService } from '../settings/services/browserService';
import { SecretValue, BrowserConfigData, BrowserConfigOptions } from '../settings/types';
import { TestCaseService } from './services/testCaseService';

const CreateTest: React.FC = () => {
  const navigate = useNavigate();
  const { selectedProject } = useProjects();
  const [method, setMethod] = useState<'upload' | 'manual'>('manual');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  
  // API Data states
  const [browserConfigOptions, setBrowserConfigOptions] = useState<BrowserConfigOptions | null>(null);
  const [existingBrowserConfigs, setExistingBrowserConfigs] = useState<BrowserConfigData[]>([]);
  const [existingSecrets, setExistingSecrets] = useState<SecretValue[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  
  // Dropdown states
  const [priorityDropdownOpen, setPriorityDropdownOpen] = useState(false);
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [browserChannelDropdowns, setBrowserChannelDropdowns] = useState<Record<string, boolean>>({});
  const [userAgentDropdowns, setUserAgentDropdowns] = useState<Record<string, boolean>>({});
  const [viewportDropdowns, setViewportDropdowns] = useState<Record<string, boolean>>({});
  const [existingBrowserConfigDropdowns, setExistingBrowserConfigDropdowns] = useState<Record<string, boolean>>({});
  const [existingSecretsDropdowns, setExistingSecretsDropdowns] = useState<Record<string, boolean>>({});

  // Load data on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoadingData(true);
        
        if (!selectedProject?.id) {
          setLoadingData(false);
          return;
        }
        
        // Fetch browser configuration options from backend constants
        try {
          const configOptions = await BrowserService.getBrowserConfigOptions();
          setBrowserConfigOptions(configOptions);
        } catch (error) {
          console.error('Failed to load browser configuration options:', error);
          setBrowserConfigOptions(null);
        }

        try {
          const browserConfigsData = await BrowserService.getBrowserConfigsByProject(selectedProject.id);
          setExistingBrowserConfigs(browserConfigsData);
        } catch (error) {
          console.error('Failed to load browser configs:', error);
          setExistingBrowserConfigs([]);
        }

        try {
          const secretsData = await BrowserService.getSecretsByProject(selectedProject.id);
          setExistingSecrets(secretsData);
        } catch (error) {
          console.error('Failed to load secrets:', error);
          setExistingSecrets([]);
        }
        
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setLoadingData(false);
      }
    };

    loadData();
  }, [selectedProject?.id]);


  
  // Form data
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    category: 'authentication',
    goal: '',
    startingUrl: '',
    allowedDomains: [''],
    extraRules: [{ id: '1', ruleNumber: 1, description: '' }],
    newBrowserConfigs: [{
      id: '1',
      browserChannel: '',
      userAgent: '',
      viewportSize: { width: 1920, height: 1080 },
      geolocation: undefined as { latitude: number; longitude: number; } | undefined
    }],
    existingBrowserConfigIds: [] as string[],
    newSecrets: [] as { id: string; secretName: string; value: string; }[],
    existingSecretIds: [] as string[]
  });

  const [file, setFile] = useState<File | null>(null);

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Extra Rules handlers
  const handleRuleChange = (index: number, value: string) => {
    const newRules = [...formData.extraRules];
    newRules[index] = { ...newRules[index], description: value };
    setFormData(prev => ({
      ...prev,
      extraRules: newRules
    }));
  };

  const addRule = () => {
    const newRule = {
      id: `rule-${Date.now()}`,
      ruleNumber: formData.extraRules.length + 1,
      description: ''
    };
    setFormData(prev => ({
      ...prev,
      extraRules: [...prev.extraRules, newRule]
    }));
  };

  const removeRule = (index: number) => {
    if (formData.extraRules.length > 1) {
      const newRules = formData.extraRules.filter((_, i) => i !== index);
      // Renumber remaining rules
      const renumberedRules = newRules.map((rule, i) => ({ ...rule, ruleNumber: i + 1 }));
      setFormData(prev => ({
        ...prev,
        extraRules: renumberedRules
      }));
    }
  };

  // Allowed Domains handlers
  const handleDomainChange = (index: number, value: string) => {
    const newDomains = [...formData.allowedDomains];
    newDomains[index] = value;
    setFormData(prev => ({
      ...prev,
      allowedDomains: newDomains
    }));
  };

  const addDomain = () => {
    setFormData(prev => ({
      ...prev,
      allowedDomains: [...prev.allowedDomains, '']
    }));
  };

  const removeDomain = (index: number) => {
    if (formData.allowedDomains.length > 1) {
      const newDomains = formData.allowedDomains.filter((_, i) => i !== index);
      setFormData(prev => ({
        ...prev,
        allowedDomains: newDomains
      }));
    }
  };

  // Browser Config handlers
  const handleNewBrowserConfigChange = (index: number, field: string, value: any) => {
    const newConfigs = [...formData.newBrowserConfigs];
    if (field === 'viewportSize.width' || field === 'viewportSize.height') {
      const [, dimension] = field.split('.');
      newConfigs[index] = {
        ...newConfigs[index],
        viewportSize: { ...newConfigs[index].viewportSize, [dimension]: value }
      };
    } else if (field.startsWith('geolocation.')) {
      const [, coord] = field.split('.');
      const currentGeo = newConfigs[index].geolocation || { latitude: 0, longitude: 0 };
      newConfigs[index] = {
        ...newConfigs[index],
        geolocation: { ...currentGeo, [coord]: value }
      };
    } else {
      newConfigs[index] = { ...newConfigs[index], [field]: value };
    }
    setFormData(prev => ({
      ...prev,
      newBrowserConfigs: newConfigs
    }));
  };

  const addNewBrowserConfig = () => {
    const newConfig = {
      id: `config-${Date.now()}`,
      browserChannel: '',
      userAgent: '',
      viewportSize: { width: 1920, height: 1080 },
      geolocation: undefined
    };
    setFormData(prev => ({
      ...prev,
      newBrowserConfigs: [...prev.newBrowserConfigs, newConfig]
    }));
  };

  const removeNewBrowserConfig = (index: number) => {
    // Allow removing all browser configs since we're bypassing backend creation for now
    const newConfigs = formData.newBrowserConfigs.filter((_, i) => i !== index);
    setFormData(prev => ({
      ...prev,
      newBrowserConfigs: newConfigs
    }));
  };

  const removeExistingBrowserConfig = (configId: string) => {
    setFormData(prev => ({
      ...prev,
      existingBrowserConfigIds: prev.existingBrowserConfigIds.filter(id => id !== configId)
    }));
  };

  // Secrets handlers
  const handleNewSecretChange = (index: number, field: string, value: string) => {
    const newSecrets = [...formData.newSecrets];
    newSecrets[index] = { ...newSecrets[index], [field]: value };
    setFormData(prev => ({
      ...prev,
      newSecrets: newSecrets
    }));
  };

  const addNewSecret = () => {
    const newSecret = {
      id: `secret-${Date.now()}`,
      secretName: '',
      value: ''
    };
    setFormData(prev => ({
      ...prev,
      newSecrets: [...prev.newSecrets, newSecret]
    }));
  };

  const removeNewSecret = (index: number) => {
    const newSecrets = formData.newSecrets.filter((_, i) => i !== index);
    setFormData(prev => ({
      ...prev,
      newSecrets: newSecrets
    }));
  };

  const removeExistingSecret = (secretId: string) => {
    setFormData(prev => ({
      ...prev,
      existingSecretIds: prev.existingSecretIds.filter(id => id !== secretId)
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Validation for the People's Republic of Code
      if (!selectedProject?.id) {
        throw new Error('Project must be selected to serve the Party!');
      }

      if (method === 'upload' && !file) {
        throw new Error('File must be uploaded for the glory of the collective!');
      }

      if (method === 'manual') {
        if (!formData.title.trim()) throw new Error('Test name is required for the Revolution!');
        if (!formData.description.trim()) throw new Error('Test description serves the people!');
        if (!formData.goal.trim()) throw new Error('Test goal advances the cause!');
        if (!formData.startingUrl.trim()) throw new Error('Starting URL guides our path!');
        if (formData.allowedDomains.every(domain => !domain.trim())) {
          throw new Error('At least one domain must serve the Party!');
        }
      }

      // Build the payload for irie backend, rastaman
      const payload = {
        project_id: selectedProject?.id || '',
        document_id: null, // File upload doesn't create documents, just parses content
        test_name: formData.title,
        test_description: formData.description,
        test_goal: formData.goal,
        extra_rules: formData.extraRules.map(rule => rule.description).filter(desc => desc.trim() !== ''),
        url_route: formData.startingUrl,
        allowed_domains: formData.allowedDomains.filter(domain => domain.trim() !== ''),
        priority: formData.priority as 'low' | 'medium' | 'high' | 'critical',
        category: formData.category,
        new_browser_configs: [], // Skip for now due to backend bug
        existing_browser_config_ids: formData.existingBrowserConfigIds,
        new_secret_values: [], // Skip for now due to backend bug  
        existing_secret_value_ids: formData.existingSecretIds
      };

      console.log('Payload for irie backend, bredrin:', payload);
      
      // Call the real API endpoint, jah bless!
      const createdTestCase = await TestCaseService.createTestCase(payload);
      console.log('Test case created successfully, rastaman!', createdTestCase);
      setSuccess(true);
      
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (error) {
      console.error('Failed to create test case for the Party:', error);
      // Alert the comrade of any issues in service of transparency
      if (error instanceof Error) {
        alert(`Comrade, there is an issue: ${error.message}`);
      } else {
        alert('An unexpected error occurred in service of the collective!');
      }
    } finally {
      setLoading(false);
    }
  };

  const priorityOptions = [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
  ];

  const categoryOptions = [
    { value: 'authentication', label: 'Authentication' },
    { value: 'banking', label: 'Banking' },
    { value: 'payments', label: 'Payments' },
    { value: 'security', label: 'Security' },
    { value: 'ui', label: 'UI' },
    { value: 'api', label: 'API' },
  ];



  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-lg p-8 border border-gray-200 text-center max-w-md mx-auto">
          <div className="w-16 h-16 bg-emerald-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-emerald-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Test Case Created!</h3>
          <p className="text-gray-600">Your test case has been successfully created and is ready to run.</p>
        </div>
      </div>
    );
  }

  // Show message if no project is selected
  if (!selectedProject) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Create Test Case</h1>
          <p className="mt-1 text-gray-600">Create a new automated test case for your application</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-amber-600 mr-3" />
            <div>
              <h3 className="text-sm font-semibold text-amber-800">No Project Selected</h3>
              <p className="text-sm text-amber-700 mt-1">Please select a project from the sidebar to create test cases.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Create Test Case</h1>
        <p className="mt-1 text-gray-600">Create a new automated test case for your application</p>
      </div>

      {/* Method Selection */}
      <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Choose Creation Method</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => setMethod('manual')}
            className={`p-6 rounded-lg border-2 transition-colors ${
              method === 'manual'
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border-gray-200 bg-white hover:border-gray-300 text-gray-700'
            }`}
          >
            <FileText className="w-8 h-8 mx-auto mb-3" />
            <h3 className="font-semibold mb-2">Manual Entry</h3>
            <p className="text-sm">Create test case by filling out the form manually</p>
          </button>
          
          <button
            onClick={() => setMethod('upload')}
            className={`p-6 rounded-lg border-2 transition-colors ${
              method === 'upload'
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border-gray-200 bg-white hover:border-gray-300 text-gray-700'
            }`}
          >
            <Upload className="w-8 h-8 mx-auto mb-3" />
            <h3 className="font-semibold mb-2">File Upload</h3>
            <p className="text-sm">Upload a test case file (.csv, .json, .txt, .doc, .docx, .pdf, .xlsx)</p>
          </button>
        </div>
      </div>

      {/* Form Content */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {method === 'upload' ? (
          <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Upload Test Case File</h2>
            
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-indigo-400 transition-colors">
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Upload your test case file</h3>
              <p className="text-gray-600 mb-4">Drag and drop your file here, or click to select</p>
              
              <input
                type="file"
                accept=".csv,.json,.txt,.doc,.docx,.pdf,.xlsx,.xls,.rtf,.odt"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer"
              >
                Select File
              </label>
              
              {file && (
                <div className="mt-4 p-3 bg-gray-50 rounded-lg flex items-center justify-between">
                  <span className="text-sm text-gray-700">{file.name}</span>
                  <button
                    type="button"
                    onClick={() => setFile(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {loadingData ? (
              <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
                <div className="flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mr-2" />
                  <span className="text-gray-600">Loading browser types and existing configurations...</span>
                </div>
              </div>
            ) : (
              <>
            {/* Basic Information */}
            <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 overflow-visible relative z-0">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Basic Information</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 overflow-visible">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Test Case Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(e) => handleInputChange('title', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
                    placeholder="e.g., User Login Authentication"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Priority *
                  </label>
                  <CustomDropdown
                    options={priorityOptions}
                    value={formData.priority}
                    onChange={(value) => handleInputChange('priority', value)}
                    isOpen={priorityDropdownOpen}
                    setIsOpen={setPriorityDropdownOpen}
                    placeholder="Select Priority"
                    fullWidth={true}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Category *
                  </label>
                  <CustomDropdown
                    options={categoryOptions}
                    value={formData.category}
                    onChange={(value) => handleInputChange('category', value)}
                    isOpen={categoryDropdownOpen}
                    setIsOpen={setCategoryDropdownOpen}
                    placeholder="Select Category"
                    fullWidth={true}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description *
                  </label>
                  <textarea
                    required
                    rows={3}
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
                    placeholder="Describe what this test case validates..."
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Test Goal *
                  </label>
                  <textarea
                    required
                    rows={2}
                    value={formData.goal}
                    onChange={(e) => handleInputChange('goal', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
                    placeholder="What should this test achieve or verify?"
                  />
                </div>
              </div>
            </div>

            {/* Test Configuration */}
            <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Test Configuration</h2>
              
              <div className="space-y-6">
                {/* Starting URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Starting URL *</label>
                  <div className="flex items-center space-x-2">
                    <Globe className="w-4 h-4 text-gray-400 ml-3" />
                    <input
                      type="url"
                      required
                      value={formData.startingUrl}
                      onChange={(e) => handleInputChange('startingUrl', e.target.value)}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                      placeholder="https://example.com"
                    />
                  </div>
                </div>

                {/* Allowed Domains */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">Allowed Domains *</label>
                    <button
                      type="button"
                      onClick={addDomain}
                      className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Add Domain
                    </button>
                  </div>
                  <div className="space-y-2">
                    {formData.allowedDomains.map((domain, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <Globe className="w-4 h-4 text-gray-400 ml-3" />
                        <input
                          type="text"
                          value={domain}
                          onChange={(e) => handleDomainChange(index, e.target.value)}
                          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                          placeholder="example.com"
                        />
                        {formData.allowedDomains.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeDomain(index)}
                            className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Browser Configurations */}
            <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 overflow-visible relative z-0">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Browser Configurations</h2>
                <button
                  type="button"
                  onClick={addNewBrowserConfig}
                  className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Config
                </button>
              </div>

              {/* Select Existing Browser Config */}
              {existingBrowserConfigs.length > 0 && (
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Or select an existing browser configuration
                  </label>
                  <CustomDropdown
                    options={existingBrowserConfigs.map(config => {
                      const viewport = config.browser_config?.viewport;
                      const userAgent = config.browser_config?.user_agent || '';
                      
                      // Extract browser type from user agent 
                      let browserType = 'Unknown';
                      if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) browserType = 'Chromium';
                      else if (userAgent.includes('Firefox')) browserType = 'Firefox';
                      else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) browserType = 'Webkit';
                      else if (userAgent.includes('Edg')) browserType = 'Microsoft Edge';
                      
                      return {
                        value: config.id,
                        label: `${browserType} - ${viewport?.width || 1920}×${viewport?.height || 1080}`
                      };
                    })}
                    value=""
                    onChange={(configId) => {
                      if (configId && !formData.existingBrowserConfigIds.includes(configId)) {
                        setFormData(prev => ({
                          ...prev,
                          existingBrowserConfigIds: [...prev.existingBrowserConfigIds, configId]
                        }));
                      }
                    }}
                    isOpen={existingBrowserConfigDropdowns['main'] || false}
                    setIsOpen={(open) => setExistingBrowserConfigDropdowns(prev => ({ ...prev, main: open }))}
                    placeholder="Select existing configuration"
                    fullWidth={true}
                  />
                </div>
              )}

              <div className="space-y-4">
                {/* Existing Browser Configs (Non-editable) */}
                {formData.existingBrowserConfigIds.map((configId) => {
                  const config = existingBrowserConfigs.find(c => c.id === configId);
                  if (!config) return null;
                  
                  const viewport = config.browser_config?.viewport;
                  const userAgent = config.browser_config?.user_agent || '';
                  
                  // Extract browser type from user agent 
                  let browserType = 'Unknown';
                  if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) browserType = 'Chromium';
                  else if (userAgent.includes('Firefox')) browserType = 'Firefox';
                  else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) browserType = 'Webkit';
                  else if (userAgent.includes('Edg')) browserType = 'Microsoft Edge';
                  
                  return (
                    <div key={configId} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <Monitor className="w-5 h-5 text-gray-600" />
                          <span className="text-sm font-medium text-gray-700">
                            {browserType} - {viewport?.width || 1920}×{viewport?.height || 1080} (Existing)
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeExistingBrowserConfig(configId)}
                          className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="text-xs text-gray-500">
                        This configuration will be reused from existing setup
                      </div>
                    </div>
                  );
                })}

                {/* New Browser Configs (Editable) */}
                {formData.newBrowserConfigs.map((config, index) => (
                  <div key={config.id} className="border border-gray-200 rounded-lg p-4 overflow-visible">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <Monitor className="w-5 h-5 text-gray-600" />
                        <span className="text-sm font-medium text-gray-700">New Browser Configuration</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeNewBrowserConfig(index)}
                        className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                        title="Remove browser configuration"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm overflow-visible">
                      <div className="md:col-span-2">
                        <label className="block text-xs font-medium text-gray-500 mb-1">Browser Channel</label>
                        <CustomDropdown
                          options={browserConfigOptions?.browser_channels.map(channel => ({ value: channel, label: channel })) || []}
                          value={config.browserChannel || ''}
                          onChange={(value) => handleNewBrowserConfigChange(index, 'browserChannel', value)}
                          isOpen={browserChannelDropdowns[config.id] || false}
                          setIsOpen={(open) => setBrowserChannelDropdowns(prev => ({ ...prev, [config.id]: open }))}
                          placeholder="Select Browser Channel"
                          fullWidth={true}
                        />
                      </div>
                      
                      <div className="md:col-span-2">
                        <label className="block text-xs font-medium text-gray-500 mb-1">User Agent</label>
                        <CustomDropdown
                          options={browserConfigOptions?.user_agents.map(agent => ({ value: agent, label: agent.slice(0, 50) + '...' })) || []}
                          value={config.userAgent || ''}
                          onChange={(value) => handleNewBrowserConfigChange(index, 'userAgent', value)}
                          isOpen={userAgentDropdowns[config.id] || false}
                          setIsOpen={(open) => setUserAgentDropdowns(prev => ({ ...prev, [config.id]: open }))}
                          placeholder="Select User Agent"
                          fullWidth={true}
                        />
                      </div>
                      
                      <div className="md:col-span-2">
                        <label className="block text-xs font-medium text-gray-500 mb-1">Viewport Size</label>
                        <CustomDropdown
                          options={browserConfigOptions?.viewport_sizes.map(viewport => ({
                            value: `${viewport.width}x${viewport.height}`,
                            label: `${viewport.width} × ${viewport.height}`
                          })) || []}
                          value={`${config.viewportSize.width}x${config.viewportSize.height}`}
                          onChange={(value) => {
                            const [width, height] = value.split('x').map(Number);
                            handleNewBrowserConfigChange(index, 'viewportSize.width', width);
                            handleNewBrowserConfigChange(index, 'viewportSize.height', height);
                          }}
                          isOpen={viewportDropdowns[config.id] || false}
                          setIsOpen={(open) => setViewportDropdowns(prev => ({ ...prev, [config.id]: open }))}
                          placeholder="Select Viewport Size"
                          fullWidth={true}
                        />
                      </div>
                      
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Latitude (optional)</label>
                        <input
                          type="number"
                          step="any"
                          value={config.geolocation?.latitude || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            if (value) {
                              handleNewBrowserConfigChange(index, 'geolocation.latitude', parseFloat(value));
                            } else {
                              handleNewBrowserConfigChange(index, 'geolocation', undefined);
                            }
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                          placeholder="e.g. 40.7128"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">Longitude (optional)</label>
                        <input
                          type="number"
                          step="any"
                          value={config.geolocation?.longitude || ''}
                          onChange={(e) => {
                            const value = e.target.value;
                            if (value) {
                              handleNewBrowserConfigChange(index, 'geolocation.longitude', parseFloat(value));
                            } else if (!config.geolocation?.latitude) {
                              handleNewBrowserConfigChange(index, 'geolocation', undefined);
                            }
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                          placeholder="e.g. -74.0060"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Secrets */}
            <div className="bg-white rounded-lg p-6 border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Secrets</h2>
                <button
                  type="button"
                  onClick={addNewSecret}
                  className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Secret
                </button>
              </div>

              {/* Select Existing Secret */}
              {existingSecrets.length > 0 && (
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Or select an existing secret
                  </label>
                  <CustomDropdown
                    options={existingSecrets.map(secret => ({
                      value: secret.id,
                      label: `${secret.secret_name} - ${new Date(secret.created_at).toLocaleDateString()}`
                    }))}
                    value=""
                    onChange={(secretId) => {
                      if (secretId && !formData.existingSecretIds.includes(secretId)) {
                        setFormData(prev => ({
                          ...prev,
                          existingSecretIds: [...prev.existingSecretIds, secretId]
                        }));
                      }
                    }}
                    isOpen={existingSecretsDropdowns['main'] || false}
                    setIsOpen={(open) => setExistingSecretsDropdowns(prev => ({ ...prev, main: open }))}
                    placeholder="Select existing secret"
                    fullWidth={true}
                  />
                </div>
              )}
                
              <div className="space-y-3">
                {/* Existing Secrets (Non-editable) */}
                {formData.existingSecretIds.map((secretId) => {
                  const secret = existingSecrets.find(s => s.id === secretId);
                  if (!secret) return null;
                  
                  return (
                    <div key={secretId} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                      <div className="flex items-center justify-between mb-2">
                        <span className="flex-1 text-sm font-medium text-gray-700 mr-4">
                          {secret.secret_name} (Existing)
                        </span>
                        <button
                          type="button"
                          onClick={() => removeExistingSecret(secretId)}
                          className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="text-xs text-gray-500">
                        This secret will be reused from existing setup
                      </div>
                    </div>
                  );
                })}

                {/* New Secrets (Editable) */}
                {formData.newSecrets.map((secret, index) => (
                  <div key={secret.id} className="border border-gray-200 rounded-lg p-4 overflow-visible">
                    <div className="flex items-center justify-between mb-2">
                      <input
                        type="text"
                        value={secret.secretName}
                        onChange={(e) => handleNewSecretChange(index, 'secretName', e.target.value)}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white text-sm mr-4"
                        placeholder="Secret name"
                      />
                      <button
                        type="button"
                        onClick={() => removeNewSecret(index)}
                        className="p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    
                    <div>
                      <input
                        type="password"
                        value={secret.value}
                        onChange={(e) => handleNewSecretChange(index, 'value', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded text-gray-800 font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                        placeholder="Secret value"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Add Secrets Button - Show when no secrets exist */}
            {formData.newSecrets.length === 0 && formData.existingSecretIds.length === 0 && (
              <div className="text-center">
                <button
                  type="button"
                  onClick={addNewSecret}
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Secrets (Optional)
                </button>
              </div>
            )}

            {/* Extra Rules */}
            <div className="bg-white rounded-lg p-6 border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Extra Rules</h2>
                <button
                  type="button"
                  onClick={addRule}
                  className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Rule
                </button>
              </div>

              <div className="space-y-3">
                {formData.extraRules.map((rule, index) => (
                  <div key={rule.id} className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center text-sm font-medium text-indigo-600 mt-1">
                      {rule.ruleNumber}
                    </div>
                    <div className="flex-1">
                      <textarea
                        value={rule.description}
                        onChange={(e) => handleRuleChange(index, e.target.value)}
                        placeholder={`Rule ${rule.ruleNumber}: Describe the rule or constraint...`}
                        rows={2}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
                      />
                    </div>
                    {formData.extraRules.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRule(index)}
                        className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors mt-1"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
              </>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-6">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-6 py-3 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          
          <button
            type="submit"
            disabled={loading || (method === 'upload' && !file) || (method === 'manual' && (!formData.title || !formData.description || !formData.goal || !formData.startingUrl || formData.allowedDomains.some(domain => !domain.trim())))}
            className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Create Test Case
              </>
            )}
          </button>
        </div>
      </form>

      {/* Help Information */}
      <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-blue-900 mb-1">Need Help?</h3>
            <p className="text-sm text-blue-800">
              Test cases should be clear, specific, and include all necessary steps to validate the expected behavior. 
              For file uploads, we support CSV, JSON, TXT, DOC, DOCX, PDF, XLSX, XLS, RTF, and ODT formats with predefined structures.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateTest; 