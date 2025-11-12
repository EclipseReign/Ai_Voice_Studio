import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Sparkles, TrendingUp, BookOpen, Lightbulb, 
  Heart, Zap, Search, Play, Clock, Users 
} from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

/**
 * TemplateLibrary Component - Pre-made templates for quick video creation
 * Inspired by Revid AI's template system
 */
const TemplateLibrary = ({ onSelectTemplate, selectedTemplate, className = "" }) => {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [previewTemplate, setPreviewTemplate] = useState(null);

  // Template categories
  const categories = [
    { id: 'all', name: t('templates.all') || 'All Templates', icon: Sparkles },
    { id: 'viral', name: t('templates.viral') || 'Viral Content', icon: TrendingUp },
    { id: 'educational', name: t('templates.educational') || 'Educational', icon: BookOpen },
    { id: 'motivational', name: t('templates.motivational') || 'Motivational', icon: Heart },
    { id: 'tips', name: t('templates.tips') || 'Tips & Tricks', icon: Lightbulb },
    { id: 'storytelling', name: t('templates.storytelling') || 'Storytelling', icon: Zap }
  ];

  // Pre-defined templates with various styles
  const templates = [
    {
      id: 'viral-hook-1',
      category: 'viral',
      name: 'Shocking Facts',
      description: 'Start with mind-blowing facts to grab attention instantly',
      thumbnail: '🤯',
      prompt: 'Create a video about [YOUR TOPIC] starting with 3 shocking facts that most people dont know. Make it engaging and surprising.',
      duration: 1,
      voice_style: 'energetic',
      video_type: 'shorts',
      subtitle_style: 'tiktok',
      background_preset: 'minecraft',
      views: '2.5M',
      engagement: '95%',
      tags: ['viral', 'facts', 'trending']
    },
    {
      id: 'viral-hook-2',
      category: 'viral',
      name: 'Did You Know?',
      description: 'Intriguing question format that keeps viewers watching',
      thumbnail: '🧠',
      prompt: 'Create a "Did you know?" style video about [YOUR TOPIC]. Start with an intriguing question and reveal the answer in an exciting way.',
      duration: 1,
      voice_style: 'mysterious',
      video_type: 'shorts',
      subtitle_style: 'tiktok',
      background_preset: 'subway_surfers',
      views: '3.1M',
      engagement: '92%',
      tags: ['viral', 'question', 'curiosity']
    },
    {
      id: 'educational-1',
      category: 'educational',
      name: 'How-To Tutorial',
      description: 'Step-by-step guide format for teaching',
      thumbnail: '📚',
      prompt: 'Create a step-by-step tutorial on how to [YOUR TOPIC]. Break it down into 5 easy-to-follow steps with clear explanations.',
      duration: 3,
      voice_style: 'clear',
      video_type: 'youtube_images',
      subtitle_style: 'minimal',
      background_preset: null,
      views: '1.2M',
      engagement: '88%',
      tags: ['educational', 'tutorial', 'howto']
    },
    {
      id: 'educational-2',
      category: 'educational',
      name: 'Explainer Video',
      description: 'Explain complex topics in simple terms',
      thumbnail: '💡',
      prompt: 'Explain [YOUR TOPIC] in simple terms that anyone can understand. Use analogies and real-world examples.',
      duration: 2,
      voice_style: 'professional',
      video_type: 'youtube_images',
      subtitle_style: 'minimal',
      background_preset: null,
      views: '890K',
      engagement: '85%',
      tags: ['educational', 'explainer', 'learning']
    },
    {
      id: 'motivational-1',
      category: 'motivational',
      name: 'Success Story',
      description: 'Inspire with powerful success narratives',
      thumbnail: '🏆',
      prompt: 'Tell an inspiring success story about [YOUR TOPIC]. Focus on the journey, struggles, and ultimate triumph.',
      duration: 2,
      voice_style: 'inspiring',
      video_type: 'youtube_images',
      subtitle_style: 'instagram',
      background_preset: null,
      views: '1.8M',
      engagement: '94%',
      tags: ['motivational', 'success', 'inspiring']
    },
    {
      id: 'motivational-2',
      category: 'motivational',
      name: 'Daily Motivation',
      description: 'Quick motivational boost for viewers',
      thumbnail: '💪',
      prompt: 'Create a powerful motivational message about [YOUR TOPIC]. Make it energizing and uplifting.',
      duration: 1,
      voice_style: 'powerful',
      video_type: 'shorts',
      subtitle_style: 'tiktok',
      background_preset: 'gta',
      views: '2.3M',
      engagement: '96%',
      tags: ['motivational', 'daily', 'energy']
    },
    {
      id: 'tips-1',
      category: 'tips',
      name: 'Top 5 Tips',
      description: 'Listicle format with actionable tips',
      thumbnail: '✨',
      prompt: 'Share the top 5 tips for [YOUR TOPIC]. Make each tip practical and immediately actionable.',
      duration: 2,
      voice_style: 'friendly',
      video_type: 'youtube_images',
      subtitle_style: 'minimal',
      background_preset: null,
      views: '1.5M',
      engagement: '89%',
      tags: ['tips', 'listicle', 'practical']
    },
    {
      id: 'tips-2',
      category: 'tips',
      name: 'Quick Life Hacks',
      description: 'Fast-paced hacks and shortcuts',
      thumbnail: '⚡',
      prompt: 'Present 3 amazing life hacks related to [YOUR TOPIC]. Make them quick, surprising, and useful.',
      duration: 1,
      voice_style: 'energetic',
      video_type: 'shorts',
      subtitle_style: 'tiktok',
      background_preset: 'satisfying',
      views: '4.2M',
      engagement: '97%',
      tags: ['tips', 'hacks', 'quick']
    },
    {
      id: 'story-1',
      category: 'storytelling',
      name: 'Story Arc',
      description: 'Classic narrative structure with beginning, middle, end',
      thumbnail: '📖',
      prompt: 'Tell a compelling story about [YOUR TOPIC] with a clear beginning, middle, and end. Build tension and deliver a satisfying conclusion.',
      duration: 3,
      voice_style: 'narrative',
      video_type: 'youtube_images',
      subtitle_style: 'minimal',
      background_preset: null,
      views: '1.1M',
      engagement: '91%',
      tags: ['storytelling', 'narrative', 'arc']
    },
    {
      id: 'story-2',
      category: 'storytelling',
      name: 'Mystery Reveal',
      description: 'Build suspense and reveal at the end',
      thumbnail: '🔍',
      prompt: 'Create a mysterious story about [YOUR TOPIC]. Build suspense throughout and deliver a surprising reveal at the end.',
      duration: 2,
      voice_style: 'mysterious',
      video_type: 'shorts',
      subtitle_style: 'instagram',
      background_preset: 'minecraft',
      views: '2.7M',
      engagement: '93%',
      tags: ['storytelling', 'mystery', 'suspense']
    }
  ];

  // Filter templates based on search and category
  const filteredTemplates = templates.filter(template => {
    const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const handleTemplateClick = (template) => {
    setPreviewTemplate(template);
  };

  const handleUseTemplate = () => {
    if (previewTemplate && onSelectTemplate) {
      onSelectTemplate(previewTemplate);
      setPreviewTemplate(null);
      // Scroll to next button after short delay
      setTimeout(() => {
        const nextButton = document.querySelector('[data-wizard-next]');
        if (nextButton) {
          nextButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 300);
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center justify-center gap-2">
          <Sparkles className="w-6 h-6 text-purple-600" />
          {t('templates.title') || 'Template Library'}
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          {t('templates.subtitle') || 'Start with proven templates based on millions of viral videos'}
        </p>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <Input
          type="text"
          placeholder={t('templates.search') || 'Search templates...'}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Category Filters */}
      <div className="flex flex-wrap gap-2">
        {categories.map(category => {
          const Icon = category.icon;
          return (
            <Button
              key={category.id}
              variant={selectedCategory === category.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(category.id)}
              className="flex items-center gap-2"
            >
              <Icon className="w-4 h-4" />
              {category.name}
            </Button>
          );
        })}
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map(template => (
          <Card
            key={template.id}
            className={`cursor-pointer hover:shadow-lg transition-all hover:scale-105 group ${
              selectedTemplate?.id === template.id 
                ? 'ring-4 ring-blue-500 bg-blue-50 dark:bg-blue-950/30' 
                : ''
            }`}
            onClick={() => handleTemplateClick(template)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="text-4xl mb-2">{template.thumbnail}</div>
                <Badge variant="secondary" className="text-xs">
                  {template.category}
                </Badge>
              </div>
              <CardTitle className="text-lg group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                {template.name}
              </CardTitle>
              <CardDescription className="text-sm line-clamp-2">
                {template.description}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {/* Stats */}
                <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                  <div className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {template.views}
                  </div>
                  <div className="flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" />
                    {template.engagement}
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {template.duration}min
                  </div>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1">
                  {template.tags.slice(0, 3).map(tag => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      #{tag}
                    </Badge>
                  ))}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="w-full group-hover:bg-blue-600 group-hover:text-white group-hover:border-blue-600 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTemplateClick(template);
                  }}
                >
                  <Play className="w-4 h-4 mr-2" />
                  {t('templates.preview') || 'Preview & Use'}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* No Results */}
      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            {t('templates.noResults') || 'No templates found. Try different keywords.'}
          </p>
        </div>
      )}

      {/* Template Preview Dialog */}
      <Dialog open={!!previewTemplate} onOpenChange={() => setPreviewTemplate(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-2xl">
              <span className="text-4xl">{previewTemplate?.thumbnail}</span>
              {previewTemplate?.name}
            </DialogTitle>
            <DialogDescription>
              {previewTemplate?.description}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Template Details */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Category</p>
                <Badge variant="secondary">{previewTemplate?.category}</Badge>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Duration</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{previewTemplate?.duration} minute(s)</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Video Type</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{previewTemplate?.video_type}</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Subtitle Style</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{previewTemplate?.subtitle_style}</p>
              </div>
            </div>

            {/* Prompt Preview */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Prompt Template</p>
              <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
                <p className="text-sm text-gray-700 dark:text-gray-300 italic">
                  "{previewTemplate?.prompt}"
                </p>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                💡 Replace [YOUR TOPIC] with your actual topic
              </p>
            </div>

            {/* Performance Stats */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Performance</p>
              <div className="flex items-center justify-around">
                <div className="text-center">
                  <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{previewTemplate?.views}</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Avg Views</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">{previewTemplate?.engagement}</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Engagement</p>
                </div>
              </div>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-2">
              {previewTemplate?.tags.map(tag => (
                <Badge key={tag} variant="outline">
                  #{tag}
                </Badge>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setPreviewTemplate(null)}
              className="flex-1"
            >
              {t('templates.cancel') || 'Cancel'}
            </Button>
            <Button
              onClick={handleUseTemplate}
              className="flex-1 bg-blue-600 hover:bg-blue-700"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              {t('templates.useTemplate') || 'Use This Template'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TemplateLibrary;