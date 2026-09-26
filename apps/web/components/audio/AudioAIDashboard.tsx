'use client'
import { VoiceCloningPanel } from './VoiceCloningPanel'
import { NoiseRemovalPanel } from './NoiseRemovalPanel'
import { SpeakerIdentificationPanel } from './SpeakerIdentificationPanel'
import { MusicGenerationPanel } from './MusicGenerationPanel'
import { PodcastSummarizationPanel } from './PodcastSummarizationPanel'
import { EmotionDetectionPanel } from './EmotionDetectionPanel'
import { SpeechToTextPanel } from './SpeechToTextPanel'
import { TextToSpeechPanel } from './TextToSpeechPanel'

export function AudioAIDashboard() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <VoiceCloningPanel />
      <NoiseRemovalPanel />
      <SpeakerIdentificationPanel />
      <MusicGenerationPanel />
      <PodcastSummarizationPanel />
      <EmotionDetectionPanel />
      <SpeechToTextPanel />
      <TextToSpeechPanel />
    </div>
  )
}
