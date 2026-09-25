import { AppShell } from '@/components/layout/app-shell';
import { HelpWidget } from '@/components/support/help-widget';
import { NpsSurvey } from '@/components/support/nps-survey';
import { FeedbackWidget } from '@/components/support/feedback-widget';
import { LiveChatWidget } from '@/components/support/live-chat-widget';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppShell>
      {children}
      <HelpWidget />
      <NpsSurvey />
      <FeedbackWidget />
      <LiveChatWidget />
    </AppShell>
  );
}
