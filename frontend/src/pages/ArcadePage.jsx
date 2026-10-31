/** /arcade and /arcade/:gameId — the Arcade (src/arcade/ArcadeApp.jsx) inside the usual page chrome. */
import { useParams } from 'react-router-dom';
import Sidebar from '@/components/Sidebar';
import { ScrollArea } from '@/components/ui/scroll-area';
import ArcadeApp from '@/arcade/ArcadeApp';
import { GAMES } from '@/arcade/core';

export default function ArcadePage({ user, refreshBalance }) {
  const { gameId } = useParams();
  return (
    <div className="flex h-screen bg-void" data-testid="arcade-page">
      <Sidebar user={user} refreshBalance={refreshBalance} />
      <div className="flex-1 overflow-hidden lg:ml-16">
        <ScrollArea className="h-full">
          {/* Telegram Mini App: start below Telegram's own buttons («Назад», «⌄ ⋮») */}
          <div className="px-4 lg:px-6 pb-bottom-nav max-w-lg mx-auto w-full min-w-0" style={{ paddingTop: 'calc(var(--tg-safe-top, 0px) + 1rem)' }}>
            <ArcadeApp initialGame={GAMES.includes(gameId) ? gameId : null} />
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
