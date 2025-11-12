import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Sparkles, TrendingUp, Zap, Copy, Check, 
  BarChart3, Lightbulb, RefreshCw 
} from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../App';

/**
 * ViralHookGenerator - Generate attention-grabbing hooks for content
 * Inspired by Revid AI's hook generation feature
 */
const ViralHookGenerator = ({ onSelectHook, className = "" }) => {
  const { t } = useTranslation();
  const [topic, setTopic] = useState('');
  const [platform, setPlatform] = useState('tiktok');
  const [customContext, setCustomContext] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [hooks, setHooks] = useState(null);
  const [selectedHook, setSelectedHook] = useState(null);
  const [copiedHook, setCopiedHook] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const platforms = [
    { id: 'tiktok', name: 'TikTok', emoji: '🎵', description: 'Short, punchy, viral' },
    { id: 'youtube', name: 'YouTube', emoji: '▶️', description: 'Engaging, detailed' },
    { id: 'instagram', name: 'Instagram', emoji: '📸', description: 'Visual, aesthetic' }
  ];

  const handleGenerateHooks = async () => {
    if (!topic.trim()) {
      toast.error('Please enter a topic');
      return;
    }

    setIsGenerating(true);
    setHooks(null);
    setSelectedHook(null);
    setAnalysisResults(null);

    try {
      const response = await axios.post(
        `${API}/hooks/generate`,
        {
          topic,
          platform,
          custom_context: customContext || null
        },
        { withCredentials: true }
      );

      if (response.data.success) {
        setHooks(response.data.hooks);
        toast.success('Hooks generated successfully!');
      }
    } catch (error) {
      console.error('Error generating hooks:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate hooks');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyHook = (hookText) => {
    navigator.clipboard.writeText(hookText);
    setCopiedHook(hookText);
    toast.success('Hook copied to clipboard!');
    setTimeout(() => setCopiedHook(null), 2000);
  };

  const handleAnalyzeHook = async (hookText) => {
    setIsAnalyzing(true);
    setAnalysisResults(null);

    try {
      const response = await axios.post(
        `${API}/hooks/analyze`,
        { hook_text: hookText },
        { withCredentials: true }
      );

      if (response.data.success) {
        setAnalysisResults(response.data.analysis);
        setSelectedHook(hookText);
      }
    } catch (error) {
      console.error('Error analyzing hook:', error);
      toast.error('Failed to analyze hook');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleUseHook = (hookText) => {
    if (onSelectHook) {
      onSelectHook(hookText);
    }
    toast.success('Hook added to your prompt!');
  };

  const getTriggerBadgeColor = (trigger) => {
    const colors = {
      'question': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'shocking': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      'curiosity': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      'transformation': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'urgency': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
    };
    return colors[trigger] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
  };

  const renderScoreBar = (score, label, color) => {
    const percentage = (score / 10) * 100;
    return (
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700 dark:text-gray-300">{label}</span>
          <span className="font-bold text-gray-900 dark:text-white">{score}/10</span>
        </div>
        <div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div 
            className={`h-full ${color} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Generator Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-500" />
            Viral Hook Generator
          </CardTitle>
          <CardDescription>
            Create attention-grabbing hooks that stop the scroll
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Topic Input */}
          <div className="space-y-2">
            <Label htmlFor="topic">Your Topic *</Label>
            <Input
              id="topic"
              placeholder="e.g., AI technology, fitness tips, cooking hacks..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={isGenerating}
            />
          </div>

          {/* Platform Selection */}
          <div className="space-y-2">
            <Label>Target Platform</Label>
            <div className="grid grid-cols-3 gap-3">
              {platforms.map(p => (
                <button
                  key={p.id}
                  onClick={() => setPlatform(p.id)}
                  disabled={isGenerating}
                  className={`
                    p-4 rounded-lg border-2 transition-all text-left
                    ${platform === p.id 
                      ? 'border-blue-600 bg-blue-50 dark:bg-blue-950/20' 
                      : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
                    }
                    ${isGenerating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                >
                  <div className="text-2xl mb-1">{p.emoji}</div>
                  <div className="font-semibold text-sm">{p.name}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">{p.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Optional Context */}
          <div className="space-y-2">
            <Label htmlFor="context">Additional Context (Optional)</Label>
            <Textarea
              id="context"
              placeholder="Add any specific details, target audience, or style preferences..."
              value={customContext}
              onChange={(e) => setCustomContext(e.target.value)}
              disabled={isGenerating}
              rows={2}
            />
          </div>

          {/* Generate Button */}
          <Button
            onClick={handleGenerateHooks}
            disabled={isGenerating || !topic.trim()}
            className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            {isGenerating ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Generating Viral Hooks...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Generate Viral Hooks
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Generated Hooks */}
      {hooks && (
        <div className="space-y-4">
          {/* Primary Hook */}
          {hooks.primary && (
            <Card className="border-2 border-green-500 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
                    <CardTitle className="text-lg">🏆 Primary Hook (Best)</CardTitle>
                  </div>
                  <Badge className="bg-green-600 text-white">Highest Potential</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="bg-white dark:bg-gray-900 p-4 rounded-lg">
                  <p className="text-lg font-medium text-gray-900 dark:text-white">
                    "{hooks.primary.hook}"
                  </p>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Badge className={getTriggerBadgeColor(hooks.primary.trigger)}>
                    {hooks.primary.trigger}
                  </Badge>
                </div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <Lightbulb className="w-4 h-4 inline mr-1" />
                  {hooks.primary.explanation}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopyHook(hooks.primary.hook)}
                    className="flex-1"
                  >
                    {copiedHook === hooks.primary.hook ? (
                      <><Check className="w-4 h-4 mr-2" /> Copied!</>
                    ) : (
                      <><Copy className="w-4 h-4 mr-2" /> Copy</>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAnalyzeHook(hooks.primary.hook)}
                    disabled={isAnalyzing}
                    className="flex-1"
                  >
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Analyze
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleUseHook(hooks.primary.hook)}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    Use
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Alternative Hook */}
          {hooks.alternative && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  💡 Alternative Hook
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-base font-medium text-gray-900 dark:text-white">
                    "{hooks.alternative.hook}"
                  </p>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Badge className={getTriggerBadgeColor(hooks.alternative.trigger)}>
                    {hooks.alternative.trigger}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {hooks.alternative.explanation}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopyHook(hooks.alternative.hook)}
                  >
                    {copiedHook === hooks.alternative.hook ? (
                      <><Check className="w-4 h-4 mr-2" /> Copied!</>
                    ) : (
                      <><Copy className="w-4 h-4 mr-2" /> Copy</>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAnalyzeHook(hooks.alternative.hook)}
                    disabled={isAnalyzing}
                  >
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Analyze
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleUseHook(hooks.alternative.hook)}
                  >
                    Use
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Backup Hook */}
          {hooks.backup && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  🛡️ Backup Hook (Safe Option)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-base font-medium text-gray-900 dark:text-white">
                    "{hooks.backup.hook}"
                  </p>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Badge className={getTriggerBadgeColor(hooks.backup.trigger)}>
                    {hooks.backup.trigger}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {hooks.backup.explanation}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopyHook(hooks.backup.hook)}
                  >
                    {copiedHook === hooks.backup.hook ? (
                      <><Check className="w-4 h-4 mr-2" /> Copied!</>
                    ) : (
                      <><Copy className="w-4 h-4 mr-2" /> Copy</>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleUseHook(hooks.backup.hook)}
                  >
                    Use
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tips */}
          {hooks.tips && hooks.tips.length > 0 && (
            <Card className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-yellow-500" />
                  Pro Tips
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {hooks.tips.map((tip, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                      <span className="text-blue-600 dark:text-blue-400 font-bold">•</span>
                      {tip}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Analysis Results */}
      {analysisResults && selectedHook && (
        <Card className="border-2 border-purple-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-6 h-6 text-purple-600" />
              Hook Performance Analysis
            </CardTitle>
            <CardDescription>
              AI-powered analysis of "{selectedHook.substring(0, 50)}..."
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Scores */}
            <div className="space-y-3">
              {analysisResults.attention_score && renderScoreBar(analysisResults.attention_score, "Attention Score", "bg-gradient-to-r from-red-500 to-orange-500")}
              {analysisResults.curiosity_score && renderScoreBar(analysisResults.curiosity_score, "Curiosity Score", "bg-gradient-to-r from-purple-500 to-pink-500")}
              {analysisResults.emotional_impact && renderScoreBar(analysisResults.emotional_impact, "Emotional Impact", "bg-gradient-to-r from-blue-500 to-cyan-500")}
              {analysisResults.shareability && renderScoreBar(analysisResults.shareability, "Shareability", "bg-gradient-to-r from-green-500 to-emerald-500")}
              {analysisResults.clarity_score && renderScoreBar(analysisResults.clarity_score, "Clarity", "bg-gradient-to-r from-indigo-500 to-purple-500")}
            </div>

            {/* Performance Prediction */}
            {analysisResults.predicted_performance && (
              <div className="bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900/20 dark:to-pink-900/20 p-4 rounded-lg">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Predicted Performance
                </p>
                <p className="text-2xl font-bold text-purple-700 dark:text-purple-300 capitalize">
                  {analysisResults.predicted_performance}
                </p>
              </div>
            )}

            {/* Strengths & Weaknesses */}
            {(analysisResults.strengths || analysisResults.weaknesses) && (
              <div className="grid grid-cols-2 gap-4">
                {analysisResults.strengths && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm text-green-700 dark:text-green-400">✓ Strengths</h4>
                    <ul className="space-y-1">
                      {analysisResults.strengths.map((strength, i) => (
                        <li key={i} className="text-xs text-gray-600 dark:text-gray-400">• {strength}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {analysisResults.weaknesses && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm text-red-700 dark:text-red-400">✗ Weaknesses</h4>
                    <ul className="space-y-1">
                      {analysisResults.weaknesses.map((weakness, i) => (
                        <li key={i} className="text-xs text-gray-600 dark:text-gray-400">• {weakness}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Suggestions */}
            {analysisResults.suggestions && analysisResults.suggestions.length > 0 && (
              <div className="bg-blue-50 dark:bg-blue-950/20 p-4 rounded-lg">
                <h4 className="font-semibold text-sm text-blue-700 dark:text-blue-400 mb-2">
                  💡 Improvement Suggestions
                </h4>
                <ul className="space-y-1">
                  {analysisResults.suggestions.map((suggestion, i) => (
                    <li key={i} className="text-sm text-gray-700 dark:text-gray-300">
                      {i + 1}. {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ViralHookGenerator;