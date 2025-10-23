import React, { useState, useEffect } from "react";
import axios from "axios";
import { API } from "../App";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { Loader2, Sparkles, Mic, Download, Clock, Volume2 } from "lucide-react";

const HomePage = () => {
  const [activeTab, setActiveTab] = useState("ai-generate");
  
  // AI Generation state
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(1);
  const [generatedText, setGeneratedText] = useState("");
  const [isGeneratingText, setIsGeneratingText] = useState(false);
  
  // Progress tracking
  const [textProgress, setTextProgress] = useState(0);
  const [textProgressMessage, setTextProgressMessage] = useState("");
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioProgressMessage, setAudioProgressMessage] = useState("");
  
  // Manual input state
  const [manualText, setManualText] = useState("");
  
  // Common state
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState("");
  const [language, setLanguage] = useState("en-US");
  const [speed, setSpeed] = useState([0]);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [history, setHistory] = useState([]);
  
  // Fetch voices on mount
  useEffect(() => {
    fetchVoices();
    fetchHistory();
  }, []);
  
  const fetchVoices = async () => {
    try {
      const response = await axios.get(API + '/voices');
      setVoices(response.data);
      if (response.data.length > 0) {
        setSelectedVoice(response.data[0].short_name);
      }
    } catch (error) {
      console.error("Error fetching voices:", error);
      toast.error("Failed to load voices");
    }
  };
  
  const fetchHistory = async () => {
    try {
      const response = await axios.get(API + '/history');
      setHistory(response.data);
    } catch (error) {
      console.error("Error fetching history:", error);
    }
  };
  
  const handleGenerateText = async () => {
    if (!prompt.trim()) {
      toast.error("Пожалуйста, введите промпт");
      return;
    }
    
    setIsGeneratingText(true);
    setTextProgress(0);
    setTextProgressMessage("Начало генерации...");
    setGeneratedText("");
    
    try {
      // Simulate progress for text generation
      const progressInterval = setInterval(() => {
        setTextProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 15;
        });
      }, 1000);
      
      // Set message based on duration
      const estimatedTime = Math.ceil(duration / 10); // Rough estimate: 1 minute per 10 minutes of content
      setTextProgressMessage(`Генерация текста... (~${estimatedTime} мин)`);
      
      const response = await axios.post(API + '/text/generate', {
        prompt: prompt,
        duration_minutes: duration,
        language: language
      });
      
      clearInterval(progressInterval);
      setTextProgress(100);
      setTextProgressMessage("Готово!");
      setGeneratedText(response.data.text);
      toast.success(`Сгенерировано ${response.data.word_count} слов!`);
      
    } catch (error) {
      console.error("Error generating text:", error);
      toast.error("Не удалось сгенерировать текст");
    } finally {
      setIsGeneratingText(false);
    }
  };
  
  const handleSynthesize = async (text) => {
    if (!text.trim()) {
      toast.error("Пожалуйста, введите текст для озвучки");
      return;
    }
    
    if (!selectedVoice) {
      toast.error("Пожалуйста, выберите голос");
      return;
    }
    
    setIsSynthesizing(true);
    setAudioProgress(0);
    setAudioProgressMessage("Начало генерации аудио...");
    setAudioUrl(null);
    
    try {
      const speedValue = speed[0];
      const rate = 1.0 + (speedValue / 100);
      
      console.log("Synthesizing with voice:", selectedVoice, "rate:", rate);
      
      // Use SSE endpoint for progress tracking
      const eventSource = new EventSource(
        `${API}/audio/synthesize-with-progress?${new URLSearchParams({
          text: text,
          voice: selectedVoice,
          rate: rate,
          language: language
        })}`
      );
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'progress' || data.type === 'info') {
          setAudioProgress(data.progress);
          setAudioProgressMessage(data.message);
        } else if (data.type === 'complete') {
          setAudioProgress(100);
          setAudioProgressMessage("Готово!");
          setAudioUrl(API + data.audio_url);
          toast.success("Аудио успешно сгенерировано!");
          eventSource.close();
          setIsSynthesizing(false);
          fetchHistory();
        } else if (data.type === 'error') {
          toast.error("Ошибка: " + data.message);
          eventSource.close();
          setIsSynthesizing(false);
        }
      };
      
      eventSource.onerror = (error) => {
        console.error("SSE Error:", error);
        toast.error("Ошибка соединения");
        eventSource.close();
        setIsSynthesizing(false);
      };
      
    } catch (error) {
      console.error("Error synthesizing audio:", error);
      toast.error("Не удалось сгенерировать аудио");
      setIsSynthesizing(false);
    }
  };
  
  const getVoicesByLanguage = () => {
    const langCode = language.split('-')[0].toLowerCase();
    return voices.filter(v => v.locale.toLowerCase().startsWith(langCode));
  };
  
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 pt-8">
          <h1 className="text-5xl lg:text-6xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent" data-testid="main-heading">
            AI Voice Studio
          </h1>
          <p className="text-lg text-slate-600">Generate text and create realistic voice narrations</p>
        </div>
        
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="main-card">
              <CardHeader>
                <CardTitle className="text-2xl">Create Voice Narration</CardTitle>
                <CardDescription>Choose your generation method</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-2 mb-6" data-testid="mode-tabs">
                    <TabsTrigger value="ai-generate" data-testid="ai-generate-tab">
                      <Sparkles className="w-4 h-4 mr-2" />
                      AI Generate
                    </TabsTrigger>
                    <TabsTrigger value="manual-input" data-testid="manual-input-tab">
                      <Mic className="w-4 h-4 mr-2" />
                      Manual Input
                    </TabsTrigger>
                  </TabsList>
                  
                  {/* AI Generate Tab */}
                  <TabsContent value="ai-generate" className="space-y-6">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="prompt">Topic / Prompt</Label>
                        <Textarea
                          id="prompt"
                          data-testid="ai-prompt-input"
                          placeholder="Enter a topic or prompt for text generation (e.g., 'The history of artificial intelligence')"
                          value={prompt}
                          onChange={(e) => setPrompt(e.target.value)}
                          rows={3}
                          className="mt-2"
                        />
                      </div>
                      
                      <div className="grid md:grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="duration">
                            <Clock className="w-4 h-4 inline mr-2" />
                            Target Duration: {duration} minute{duration !== 1 ? 's' : ''}
                          </Label>
                          <Slider
                            id="duration"
                            data-testid="duration-slider"
                            value={[duration]}
                            onValueChange={(val) => setDuration(val[0])}
                            min={1}
                            max={60}
                            step={1}
                            className="mt-2"
                          />
                        </div>
                        
                        <div>
                          <Label htmlFor="ai-language">Language</Label>
                          <Select value={language} onValueChange={setLanguage}>
                            <SelectTrigger id="ai-language" data-testid="ai-language-select" className="mt-2">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="en-US">English (US)</SelectItem>
                              <SelectItem value="en-GB">English (UK)</SelectItem>
                              <SelectItem value="es-ES">Spanish</SelectItem>
                              <SelectItem value="fr-FR">French</SelectItem>
                              <SelectItem value="de-DE">German</SelectItem>
                              <SelectItem value="it-IT">Italian</SelectItem>
                              <SelectItem value="pt-BR">Portuguese (BR)</SelectItem>
                              <SelectItem value="ru-RU">Russian</SelectItem>
                              <SelectItem value="zh-CN">Chinese (Simplified)</SelectItem>
                              <SelectItem value="ja-JP">Japanese</SelectItem>
                              <SelectItem value="ar-SA">Arabic</SelectItem>
                              <SelectItem value="hi-IN">Hindi</SelectItem>
                              <SelectItem value="ko-KR">Korean</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      
                      <Button 
                        onClick={handleGenerateText}
                        disabled={isGeneratingText}
                        className="w-full"
                        size="lg"
                        data-testid="generate-text-button"
                      >
                        {isGeneratingText ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Генерация текста...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4 mr-2" />
                            Сгенерировать текст
                          </>
                        )}
                      </Button>
                      
                      {isGeneratingText && (
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{textProgressMessage}</span>
                            <span className="font-medium">{textProgress}%</span>
                          </div>
                          <Progress value={textProgress} className="h-2" />
                        </div>
                      )}
                      
                      {generatedText && (
                        <div className="space-y-4">
                          <div>
                            <Label htmlFor="generated-text">Generated Text (editable)</Label>
                            <Textarea
                              id="generated-text"
                              data-testid="generated-text-display"
                              value={generatedText}
                              onChange={(e) => setGeneratedText(e.target.value)}
                              rows={12}
                              className="mt-2 font-mono text-sm"
                            />
                          </div>
                          
                          <Button 
                            onClick={() => handleSynthesize(generatedText)}
                            disabled={isSynthesizing}
                            className="w-full"
                            size="lg"
                            data-testid="synthesize-ai-button"
                          >
                            {isSynthesizing ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Генерация аудио...
                              </>
                            ) : (
                              <>
                                <Volume2 className="w-4 h-4 mr-2" />
                                Озвучить текст
                              </>
                            )}
                          </Button>
                          
                          {isSynthesizing && (
                            <div className="space-y-2">
                              <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">{audioProgressMessage}</span>
                                <span className="font-medium">{audioProgress}%</span>
                              </div>
                              <Progress value={audioProgress} className="h-2" />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </TabsContent>
                  
                  {/* Manual Input Tab */}
                  <TabsContent value="manual-input" className="space-y-6">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="manual-text">Your Text</Label>
                        <Textarea
                          id="manual-text"
                          data-testid="manual-text-input"
                          placeholder="Paste or type your text here..."
                          value={manualText}
                          onChange={(e) => setManualText(e.target.value)}
                          rows={15}
                          className="mt-2 font-mono text-sm"
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="manual-language">Language</Label>
                        <Select value={language} onValueChange={setLanguage}>
                          <SelectTrigger id="manual-language" data-testid="manual-language-select" className="mt-2">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="en-US">English (US)</SelectItem>
                            <SelectItem value="en-GB">English (UK)</SelectItem>
                            <SelectItem value="es-ES">Spanish</SelectItem>
                            <SelectItem value="fr-FR">French</SelectItem>
                            <SelectItem value="de-DE">German</SelectItem>
                            <SelectItem value="it-IT">Italian</SelectItem>
                            <SelectItem value="pt-BR">Portuguese (BR)</SelectItem>
                            <SelectItem value="ru-RU">Russian</SelectItem>
                            <SelectItem value="zh-CN">Chinese (Simplified)</SelectItem>
                            <SelectItem value="ja-JP">Japanese</SelectItem>
                            <SelectItem value="ar-SA">Arabic</SelectItem>
                            <SelectItem value="hi-IN">Hindi</SelectItem>
                            <SelectItem value="ko-KR">Korean</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <Button 
                        onClick={() => handleSynthesize(manualText)}
                        disabled={isSynthesizing}
                        className="w-full"
                        size="lg"
                        data-testid="synthesize-manual-button"
                      >
                        {isSynthesizing ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Генерация аудио...
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-4 h-4 mr-2" />
                            Озвучить текст
                          </>
                        )}
                      </Button>
                      
                      {isSynthesizing && (
                        <div className="space-y-2 mt-4">
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{audioProgressMessage}</span>
                            <span className="font-medium">{audioProgress}%</span>
                          </div>
                          <Progress value={audioProgress} className="h-2" />
                        </div>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
          
          {/* Settings Panel */}
          <div className="space-y-6">
            <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="settings-card">
              <CardHeader>
                <CardTitle>Voice Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="language-setting">Language</Label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger id="language-setting" data-testid="language-setting-select" className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en-US">English (US)</SelectItem>
                      <SelectItem value="en-GB">English (UK)</SelectItem>
                      <SelectItem value="es-ES">Spanish</SelectItem>
                      <SelectItem value="fr-FR">French</SelectItem>
                      <SelectItem value="de-DE">German</SelectItem>
                      <SelectItem value="it-IT">Italian</SelectItem>
                      <SelectItem value="pt-BR">Portuguese (BR)</SelectItem>
                      <SelectItem value="ru-RU">Russian</SelectItem>
                      <SelectItem value="zh-CN">Chinese (Simplified)</SelectItem>
                      <SelectItem value="ja-JP">Japanese</SelectItem>
                      <SelectItem value="ar-SA">Arabic</SelectItem>
                      <SelectItem value="hi-IN">Hindi</SelectItem>
                      <SelectItem value="ko-KR">Korean</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label htmlFor="voice">Voice</Label>
                  <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                    <SelectTrigger id="voice" data-testid="voice-select" className="mt-2">
                      <SelectValue placeholder="Select a voice" />
                    </SelectTrigger>
                    <SelectContent className="max-h-64">
                      {getVoicesByLanguage().map((voice) => (
                        <SelectItem key={voice.short_name} value={voice.short_name}>
                          {voice.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-500 mt-1">Neural TTS voices powered by Piper</p>
                </div>
                
                <div>
                  <Label htmlFor="speed">
                    Speed: {speed[0] > 0 ? '+' : ''}{speed[0]}% ({(1 + speed[0]/100).toFixed(1)}x)
                  </Label>
                  <Slider
                    id="speed"
                    data-testid="speed-slider"
                    value={speed}
                    onValueChange={setSpeed}
                    min={-50}
                    max={100}
                    step={10}
                    className="mt-2"
                  />
                  <p className="text-xs text-slate-500 mt-1">Adjust speech speed (0.5x to 2.0x)</p>
                </div>
              </CardContent>
            </Card>
            
            {/* Audio Player */}
            {audioUrl && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="audio-player-card">
                <CardHeader>
                  <CardTitle>Generated Audio</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <audio controls className="w-full" data-testid="audio-player" key={audioUrl}>
                    <source src={audioUrl} type="audio/wav" />
                    <source src={audioUrl} type="audio/mpeg" />
                    Your browser does not support the audio element.
                  </audio>
                  <a href={audioUrl} download>
                    <Button className="w-full" variant="outline" data-testid="download-button">
                      <Download className="w-4 h-4 mr-2" />
                      Download Audio
                    </Button>
                  </a>
                </CardContent>
              </Card>
            )}
            
            {/* History */}
            {history.length > 0 && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="history-card">
                <CardHeader>
                  <CardTitle>Recent Generations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {history.slice(0, 5).map((item) => (
                      <div key={item.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200" data-testid={'history-item-' + item.id}>
                        <p className="text-sm text-slate-700 mb-2">{item.text}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                          <a href={process.env.REACT_APP_BACKEND_URL + item.audio_url} download>
                            <Button size="sm" variant="ghost" data-testid={'history-download-' + item.id}>
                              <Download className="w-3 h-3" />
                            </Button>
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;