import { useReducer, useCallback } from 'react';

export interface ExtraRule {
  id: string;
  ruleNumber: number;
  description: string;
}

export interface BrowserConfig {
  id: string;
  browserChannel: string;
  userAgent: string;
  viewportSize: { width: number; height: number };
  geolocation?: { latitude: number; longitude: number };
}

export interface Secret {
  id: string;
  key: string;
  value: string;
}

export interface CreateTestFormState {
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  goal: string;
  startingUrl: string;
  allowedDomains: string[];
  extraRules: ExtraRule[];
  newBrowserConfigs: BrowserConfig[];
  existingBrowserConfigIds: string[];
  newSecrets: Secret[];
  existingSecretIds: string[];
}

export type CreateTestFormAction =
  | { type: 'SET_FIELD'; field: keyof CreateTestFormState; value: any }
  | { type: 'UPDATE_RULE'; index: number; value: string }
  | { type: 'ADD_RULE' }
  | { type: 'REMOVE_RULE'; index: number }
  | { type: 'UPDATE_DOMAIN'; index: number; value: string }
  | { type: 'ADD_DOMAIN' }
  | { type: 'REMOVE_DOMAIN'; index: number }
  | { type: 'UPDATE_BROWSER_CONFIG'; index: number; field: string; value: any }
  | { type: 'ADD_BROWSER_CONFIG' }
  | { type: 'REMOVE_BROWSER_CONFIG'; index: number }
  | { type: 'ADD_EXISTING_BROWSER_CONFIG'; configId: string }
  | { type: 'REMOVE_EXISTING_BROWSER_CONFIG'; configId: string }
  | { type: 'UPDATE_SECRET'; index: number; field: string; value: string }
  | { type: 'ADD_SECRET' }
  | { type: 'REMOVE_SECRET'; index: number }
  | { type: 'ADD_EXISTING_SECRET'; secretId: string }
  | { type: 'REMOVE_EXISTING_SECRET'; secretId: string }
  | { type: 'RESET_FORM' };

const initialState: CreateTestFormState = {
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
    geolocation: undefined
  }],
  existingBrowserConfigIds: [],
  newSecrets: [],
  existingSecretIds: []
};

function createTestFormReducer(
  state: CreateTestFormState, 
  action: CreateTestFormAction
): CreateTestFormState {
  switch (action.type) {
    case 'SET_FIELD':
      return {
        ...state,
        [action.field]: action.value
      };

    case 'UPDATE_RULE':
      return {
        ...state,
        extraRules: state.extraRules.map((rule, index) =>
          index === action.index
            ? { ...rule, description: action.value }
            : rule
        )
      };

    case 'ADD_RULE':
      return {
        ...state,
        extraRules: [
          ...state.extraRules,
          {
            id: String(state.extraRules.length + 1),
            ruleNumber: state.extraRules.length + 1,
            description: ''
          }
        ]
      };

    case 'REMOVE_RULE':
      if (state.extraRules.length <= 1) return state;
      return {
        ...state,
        extraRules: state.extraRules.filter((_, index) => index !== action.index)
      };

    case 'UPDATE_DOMAIN':
      return {
        ...state,
        allowedDomains: state.allowedDomains.map((domain, index) =>
          index === action.index ? action.value : domain
        )
      };

    case 'ADD_DOMAIN':
      return {
        ...state,
        allowedDomains: [...state.allowedDomains, '']
      };

    case 'REMOVE_DOMAIN':
      if (state.allowedDomains.length <= 1) return state;
      return {
        ...state,
        allowedDomains: state.allowedDomains.filter((_, index) => index !== action.index)
      };

    case 'UPDATE_BROWSER_CONFIG':
      return {
        ...state,
        newBrowserConfigs: state.newBrowserConfigs.map((config, index) =>
          index === action.index
            ? { ...config, [action.field]: action.value }
            : config
        )
      };

    case 'ADD_BROWSER_CONFIG':
      return {
        ...state,
        newBrowserConfigs: [
          ...state.newBrowserConfigs,
          {
            id: String(state.newBrowserConfigs.length + 1),
            browserChannel: '',
            userAgent: '',
            viewportSize: { width: 1920, height: 1080 },
            geolocation: undefined
          }
        ]
      };

    case 'REMOVE_BROWSER_CONFIG':
      if (state.newBrowserConfigs.length <= 1) return state;
      return {
        ...state,
        newBrowserConfigs: state.newBrowserConfigs.filter((_, index) => index !== action.index)
      };

    case 'ADD_EXISTING_BROWSER_CONFIG':
      if (state.existingBrowserConfigIds.includes(action.configId)) return state;
      return {
        ...state,
        existingBrowserConfigIds: [...state.existingBrowserConfigIds, action.configId]
      };

    case 'REMOVE_EXISTING_BROWSER_CONFIG':
      return {
        ...state,
        existingBrowserConfigIds: state.existingBrowserConfigIds.filter(
          id => id !== action.configId
        )
      };

    case 'UPDATE_SECRET':
      return {
        ...state,
        newSecrets: state.newSecrets.map((secret, index) =>
          index === action.index
            ? { ...secret, [action.field]: action.value }
            : secret
        )
      };

    case 'ADD_SECRET':
      return {
        ...state,
        newSecrets: [
          ...state.newSecrets,
          {
            id: String(state.newSecrets.length + 1),
            key: '',
            value: ''
          }
        ]
      };

    case 'REMOVE_SECRET':
      return {
        ...state,
        newSecrets: state.newSecrets.filter((_, index) => index !== action.index)
      };

    case 'ADD_EXISTING_SECRET':
      if (state.existingSecretIds.includes(action.secretId)) return state;
      return {
        ...state,
        existingSecretIds: [...state.existingSecretIds, action.secretId]
      };

    case 'REMOVE_EXISTING_SECRET':
      return {
        ...state,
        existingSecretIds: state.existingSecretIds.filter(
          id => id !== action.secretId
        )
      };

    case 'RESET_FORM':
      return initialState;

    default:
      return state;
  }
}

export interface UseCreateTestReducerResult {
  formState: CreateTestFormState;
  setField: (field: keyof CreateTestFormState, value: any) => void;
  updateRule: (index: number, value: string) => void;
  addRule: () => void;
  removeRule: (index: number) => void;
  updateDomain: (index: number, value: string) => void;
  addDomain: () => void;
  removeDomain: (index: number) => void;
  updateBrowserConfig: (index: number, field: string, value: any) => void;
  addBrowserConfig: () => void;
  removeBrowserConfig: (index: number) => void;
  addExistingBrowserConfig: (configId: string) => void;
  removeExistingBrowserConfig: (configId: string) => void;
  updateSecret: (index: number, field: string, value: string) => void;
  addSecret: () => void;
  removeSecret: (index: number) => void;
  addExistingSecret: (secretId: string) => void;
  removeExistingSecret: (secretId: string) => void;
  resetForm: () => void;
}

export const useCreateTestReducer = (): UseCreateTestReducerResult => {
  const [formState, dispatch] = useReducer(createTestFormReducer, initialState);

  const setField = useCallback((field: keyof CreateTestFormState, value: any) => {
    dispatch({ type: 'SET_FIELD', field, value });
  }, []);

  const updateRule = useCallback((index: number, value: string) => {
    dispatch({ type: 'UPDATE_RULE', index, value });
  }, []);

  const addRule = useCallback(() => {
    dispatch({ type: 'ADD_RULE' });
  }, []);

  const removeRule = useCallback((index: number) => {
    dispatch({ type: 'REMOVE_RULE', index });
  }, []);

  const updateDomain = useCallback((index: number, value: string) => {
    dispatch({ type: 'UPDATE_DOMAIN', index, value });
  }, []);

  const addDomain = useCallback(() => {
    dispatch({ type: 'ADD_DOMAIN' });
  }, []);

  const removeDomain = useCallback((index: number) => {
    dispatch({ type: 'REMOVE_DOMAIN', index });
  }, []);

  const updateBrowserConfig = useCallback((index: number, field: string, value: any) => {
    dispatch({ type: 'UPDATE_BROWSER_CONFIG', index, field, value });
  }, []);

  const addBrowserConfig = useCallback(() => {
    dispatch({ type: 'ADD_BROWSER_CONFIG' });
  }, []);

  const removeBrowserConfig = useCallback((index: number) => {
    dispatch({ type: 'REMOVE_BROWSER_CONFIG', index });
  }, []);

  const addExistingBrowserConfig = useCallback((configId: string) => {
    dispatch({ type: 'ADD_EXISTING_BROWSER_CONFIG', configId });
  }, []);

  const removeExistingBrowserConfig = useCallback((configId: string) => {
    dispatch({ type: 'REMOVE_EXISTING_BROWSER_CONFIG', configId });
  }, []);

  const updateSecret = useCallback((index: number, field: string, value: string) => {
    dispatch({ type: 'UPDATE_SECRET', index, field, value });
  }, []);

  const addSecret = useCallback(() => {
    dispatch({ type: 'ADD_SECRET' });
  }, []);

  const removeSecret = useCallback((index: number) => {
    dispatch({ type: 'REMOVE_SECRET', index });
  }, []);

  const addExistingSecret = useCallback((secretId: string) => {
    dispatch({ type: 'ADD_EXISTING_SECRET', secretId });
  }, []);

  const removeExistingSecret = useCallback((secretId: string) => {
    dispatch({ type: 'REMOVE_EXISTING_SECRET', secretId });
  }, []);

  const resetForm = useCallback(() => {
    dispatch({ type: 'RESET_FORM' });
  }, []);

  return {
    formState,
    setField,
    updateRule,
    addRule,
    removeRule,
    updateDomain,
    addDomain,
    removeDomain,
    updateBrowserConfig,
    addBrowserConfig,
    removeBrowserConfig,
    addExistingBrowserConfig,
    removeExistingBrowserConfig,
    updateSecret,
    addSecret,
    removeSecret,
    addExistingSecret,
    removeExistingSecret,
    resetForm,
  };
};
