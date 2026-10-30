import { Loader2, CheckCircle2, Wrench } from 'lucide-react';
import type { ToolExecution } from '../types';

interface Props {
  tool: ToolExecution;
}

export const ToolExecutionChip = ({ tool }: Props) => {
  const isRunning = tool.status === 'running';

  return (
    <div
      className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
        isRunning
          ? 'bg-amber-50 text-amber-900 border-amber-300 animate-pulse'
          : 'bg-emerald-50 text-emerald-800 border-emerald-200'
      }`}
    >
      {isRunning ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-600" />
      ) : (
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
      )}
      <span className="font-semibold">{tool.label || tool.tool}</span>
      {tool.input && Object.keys(tool.input).length > 0 && (
        <span className="text-[11px] opacity-75 hidden sm:inline">
          ({Object.entries(tool.input).map(([k, v]) => `${k}: ${v}`).slice(0, 2).join(', ')})
        </span>
      )}
    </div>
  );
};

export const ToolCallGroup = ({ tools }: { tools: ToolExecution[] }) => {
  if (!tools || tools.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 my-2 p-2.5 rounded-xl bg-stone-50 border border-stone-200/80">
      <div className="flex items-center space-x-1.5 text-xs text-stone-500 font-medium mr-1">
        <Wrench className="w-3.5 h-3.5" />
        <span>Agent Actions:</span>
      </div>
      {tools.map((t, idx) => (
        <ToolExecutionChip key={`${t.tool}-${idx}`} tool={t} />
      ))}
    </div>
  );
};
