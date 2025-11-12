import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ChevronRight, ChevronLeft, Check, Sparkles, Mic, Video, Wand2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

/**
 * VideoWizard Component - Step-by-step video creation wizard
 * Inspired by Revid AI's multi-step workflow
 */
const VideoWizard = ({ 
  children, 
  currentStep, 
  onStepChange,
  canProceed,
  totalSteps = 5
}) => {
  const { t } = useTranslation();

  const steps = [
    { 
      id: 1, 
      name: t('wizard.step1'), 
      icon: Sparkles,
      description: t('wizard.step1Desc') || 'Choose how to create your content'
    },
    { 
      id: 2, 
      name: t('wizard.step2'), 
      icon: Wand2,
      description: t('wizard.step2Desc') || 'Generate or write your script'
    },
    { 
      id: 3, 
      name: t('wizard.step3'), 
      icon: Mic,
      description: t('wizard.step3Desc') || 'Select voice and generate audio'
    },
    { 
      id: 4, 
      name: t('wizard.step4'), 
      icon: Video,
      description: t('wizard.step4Desc') || 'Customize video settings'
    },
    { 
      id: 5, 
      name: t('wizard.step5'), 
      icon: Check,
      description: t('wizard.step5Desc') || 'Preview and render'
    }
  ];

  const progress = ((currentStep - 1) / (totalSteps - 1)) * 100;

  const handleNext = () => {
    if (currentStep < totalSteps && canProceed) {
      onStepChange(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      onStepChange(currentStep - 1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('wizard.progress')}: {t('wizard.step')} {currentStep} {t('wizard.of')} {totalSteps}
          </h3>
          <Badge variant="outline" className="bg-blue-50 dark:bg-blue-900/20">
            {Math.round(progress)}% {t('wizard.complete')}
          </Badge>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Step Indicators */}
      <div className="flex justify-between items-center relative">
        {/* Connection Line */}
        <div className="absolute top-5 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-700 -z-10" />
        
        {steps.map((step, index) => {
          const StepIcon = step.icon;
          const isCompleted = currentStep > step.id;
          const isCurrent = currentStep === step.id;
          const isUpcoming = currentStep < step.id;

          return (
            <div key={step.id} className="flex flex-col items-center flex-1">
              <button
                onClick={() => {
                  // Allow clicking on completed steps or current step
                  if (step.id <= currentStep) {
                    onStepChange(step.id);
                  }
                }}
                disabled={step.id > currentStep}
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center transition-all
                  ${isCompleted ? 'bg-green-500 text-white shadow-md' : ''}
                  ${isCurrent ? 'bg-blue-600 text-white shadow-lg ring-4 ring-blue-200 dark:ring-blue-800 scale-110' : ''}
                  ${isUpcoming ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500' : ''}
                  ${step.id <= currentStep ? 'cursor-pointer hover:scale-105' : 'cursor-not-allowed'}
                `}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <StepIcon className="w-5 h-5" />
                )}
              </button>
              <div className="mt-2 text-center max-w-[100px]">
                <p className={`text-xs font-medium ${isCurrent ? 'text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-400'}`}>
                  {step.name}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current Step Description */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border-blue-200 dark:border-blue-800">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            {React.createElement(steps[currentStep - 1].icon, { className: "w-5 h-5 text-blue-600 dark:text-blue-400" })}
            {steps[currentStep - 1].name}
          </CardTitle>
          <CardDescription className="text-sm">
            {steps[currentStep - 1].description}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Step Content */}
      <div className="min-h-[400px]">
        {children}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-700">
        <Button
          variant="outline"
          onClick={handleBack}
          disabled={currentStep === 1}
          className="flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" />
          {t('wizard.back')}
        </Button>

        <div className="flex items-center gap-3">
          {!canProceed && currentStep < totalSteps && (
            <p className="text-sm text-amber-600 dark:text-amber-400">
              {t('wizard.completeStep')}
            </p>
          )}
          
          {currentStep < totalSteps && (
            <Button
              onClick={handleNext}
              disabled={!canProceed}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
            >
              {t('wizard.next')}
              <ChevronRight className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoWizard;