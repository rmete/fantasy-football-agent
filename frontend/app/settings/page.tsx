'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  setSleeperUsername,
  setDefaultScoringFormat,
  setLLMProvider,
  setSelectedModel,
  setTemperature,
  setEnableNotifications,
  resetSettings,
  type LLMProvider,
  type AIModel,
  type ClaudeModel,
  type OpenAIModel,
  type GeminiModel,
} from '@/store/slices/settingsSlice';
import { Settings, User, Brain, Zap, Bell, RotateCcw } from 'lucide-react';
import { useState } from 'react';

export default function SettingsPage() {
  const dispatch = useAppDispatch();
  const settings = useAppSelector((state) => state.settings);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      // Send settings to backend API
      const response = await fetch('http://localhost:8000/api/v1/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          anthropic_model: settings.selectedModel,
          llm_provider: settings.llmProvider,
          sleeper_username: settings.sleeperUsername,
        }),
      });

      if (response.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } else {
        console.error('Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
      dispatch(resetSettings());
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
  };

  const claudeModels: { value: ClaudeModel; label: string; description: string }[] = [
    {
      value: 'claude-sonnet-4-5-20250929',
      label: 'Claude Sonnet 4.5',
      description: '🔥 Latest & most intelligent (Sep 2025)',
    },
    {
      value: 'claude-3-5-sonnet-20241022',
      label: 'Claude 3.5 Sonnet',
      description: 'Powerful & balanced (Oct 2024)',
    },
    {
      value: 'claude-3-5-haiku-20241022',
      label: 'Claude 3.5 Haiku',
      description: 'Fast & efficient (Oct 2024)',
    },
  ];

  const openaiModels: { value: OpenAIModel; label: string; description: string }[] = [
    {
      value: 'gpt-4o',
      label: 'GPT-4o',
      description: 'Latest multimodal model',
    },
    {
      value: 'gpt-4o-mini',
      label: 'GPT-4o Mini',
      description: 'Fast and affordable',
    },
    {
      value: 'gpt-4-turbo',
      label: 'GPT-4 Turbo',
      description: 'Previous generation flagship',
    },
  ];

  const geminiModels: { value: GeminiModel; label: string; description: string }[] = [
    {
      value: 'gemini-1.5-pro',
      label: 'Gemini 1.5 Pro',
      description: 'Most capable model',
    },
    {
      value: 'gemini-1.5-flash',
      label: 'Gemini 1.5 Flash',
      description: 'Fast and efficient',
    },
  ];

  const getModelsForProvider = () => {
    if (settings.llmProvider === 'anthropic') return claudeModels;
    if (settings.llmProvider === 'openai') return openaiModels;
    if (settings.llmProvider === 'gemini') return geminiModels;
    return [];
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold flex items-center gap-3">
            <Settings className="h-10 w-10" />
            Settings
          </h1>
          <p className="text-muted-foreground mt-2">
            Customize your fantasy football AI manager experience
          </p>
        </div>
        {saved && (
          <Badge variant="default" className="bg-green-600">
            Settings Saved!
          </Badge>
        )}
      </div>

      <div className="space-y-6">
        {/* Sleeper Account Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Sleeper Account
            </CardTitle>
            <CardDescription>
              Connect your Sleeper account to access your leagues and rosters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Sleeper Username
              </label>
              <input
                type="text"
                value={settings.sleeperUsername}
                onChange={(e) => dispatch(setSleeperUsername(e.target.value))}
                className="w-full px-3 py-2 border border-input rounded-md bg-background"
                placeholder="Enter your Sleeper username"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Your Sleeper username is used to fetch your leagues and teams
              </p>
            </div>
          </CardContent>
        </Card>

        {/* AI Model Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              AI Model Configuration
            </CardTitle>
            <CardDescription>
              Choose which AI model powers your fantasy football assistant
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Provider Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">LLM Provider</label>
              <div className="grid grid-cols-3 gap-3">
                {(['anthropic', 'openai', 'gemini'] as LLMProvider[]).map((provider) => (
                  <Button
                    key={provider}
                    variant={settings.llmProvider === provider ? 'default' : 'outline'}
                    className="w-full"
                    onClick={() => dispatch(setLLMProvider(provider))}
                  >
                    {provider === 'anthropic' && 'Anthropic'}
                    {provider === 'openai' && 'OpenAI'}
                    {provider === 'gemini' && 'Google Gemini'}
                  </Button>
                ))}
              </div>
            </div>

            {/* Model Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Model</label>
              <div className="space-y-2">
                {getModelsForProvider().map((model) => (
                  <div
                    key={model.value}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      settings.selectedModel === model.value
                        ? 'border-primary bg-primary/5'
                        : 'border-input hover:border-primary/50'
                    }`}
                    onClick={() => dispatch(setSelectedModel(model.value as AIModel))}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{model.label}</div>
                        <div className="text-sm text-muted-foreground">
                          {model.description}
                        </div>
                      </div>
                      {settings.selectedModel === model.value && (
                        <Badge variant="default">Selected</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Temperature Slider */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Temperature (Creativity): {settings.temperature.toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.temperature}
                onChange={(e) => dispatch(setTemperature(parseFloat(e.target.value)))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>More Focused (0.0)</span>
                <span>More Creative (1.0)</span>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Lower values make responses more consistent and focused. Higher values
                make them more creative and varied.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Fantasy Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Fantasy Settings
            </CardTitle>
            <CardDescription>
              Default preferences for projections and analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Default Scoring Format
              </label>
              <div className="grid grid-cols-3 gap-3">
                {(['PPR', 'HALF_PPR', 'STD'] as const).map((format) => (
                  <Button
                    key={format}
                    variant={
                      settings.defaultScoringFormat === format ? 'default' : 'outline'
                    }
                    onClick={() => dispatch(setDefaultScoringFormat(format))}
                  >
                    {format === 'HALF_PPR' ? '0.5 PPR' : format}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
            <CardDescription>
              Manage notification preferences (coming soon)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Enable Notifications</div>
                <div className="text-sm text-muted-foreground">
                  Get alerts for waiver wire opportunities and injury updates
                </div>
              </div>
              <Button
                variant={settings.enableNotifications ? 'default' : 'outline'}
                size="sm"
                onClick={() =>
                  dispatch(setEnableNotifications(!settings.enableNotifications))
                }
              >
                {settings.enableNotifications ? 'Enabled' : 'Disabled'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex items-center justify-between pt-4">
          <Button variant="outline" onClick={handleReset} className="gap-2">
            <RotateCcw className="h-4 w-4" />
            Reset to Defaults
          </Button>
          <Button onClick={handleSave} size="lg" disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings to Backend'}
          </Button>
        </div>
      </div>
    </div>
  );
}
