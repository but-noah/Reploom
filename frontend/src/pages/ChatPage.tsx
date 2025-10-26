import { Button } from '@/components/ui/button';
import useAuth, { getLoginUrl, getSignupUrl } from '@/lib/use-auth';
import { LogIn, UserPlus } from 'lucide-react';
import GuideInfoBox from '@/components/guide/guide-info-box';
import { ChatWindow } from '@/components/chat-window';

export default function ChatPage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] my-auto gap-4">
        <h2 className="text-xl">You are not logged in</h2>
        <div className="flex gap-4">
          <Button asChild variant="default" size="default">
            <a href={getLoginUrl()} className="flex items-center gap-2">
              <LogIn />
              <span>Login</span>
            </a>
          </Button>
          <Button asChild variant="default" size="default">
            <a href={getSignupUrl()} className="flex items-center gap-2">
              <UserPlus />
              <span>Sign up</span>
            </a>
          </Button>
        </div>
      </div>
    );
  }

  const InfoCard = (
    <GuideInfoBox>
      <ul>
        <li className="text-l">
          🤝
          <span className="ml-2">
            This template showcases a simple chatbot using{' '}
            <a className="text-blue-500" href="https://www.langchain.com/langgraph" target="_blank">
              LangGraph
            </a>{' '}
            in a{' '}
            <a className="text-blue-500" href="https://fastapi.tiangolo.com/" target="_blank">
              FastAPI
            </a>{' '}
            project.
          </span>
        </li>
        <li className="hidden text-l md:block">
          💻
          <span className="ml-2">
            You can find the prompt and model logic for this use-case in{' '}
            <code>backend/app/api/routes/chat.py</code>.
          </span>
        </li>
        <li className="hidden text-l md:block">
          🎨
          <span className="ml-2">
            The main frontend logic is found in <code>/frontend/src/pages/ChatPage.tsx</code>.
          </span>
        </li>
        <li className="text-l">
          👇
          <span className="ml-2">
            Try asking e.g. <code>What can you help me with?</code> below!
          </span>
        </li>
      </ul>
    </GuideInfoBox>
  );

  return (
    <ChatWindow
      endpoint="/api/agent"
      emoji="🤖"
      placeholder={`Hello ${user?.name}, I'm your personal assistant. How can I help you today?`}
      emptyStateComponent={InfoCard}
    />
  );
}
