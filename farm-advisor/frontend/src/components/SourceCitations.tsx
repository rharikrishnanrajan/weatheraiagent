import { FileText, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  sources: string[];
}

export const SourceCitations = ({ sources }: Props) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-stone-200/80">
      <div className="flex items-center space-x-1.5 text-xs font-semibold text-stone-500 mb-2">
        <FileText className="w-3.5 h-3.5 text-farm-600" />
        <span>Grounded Knowledge Base Sources:</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {sources.map((src, idx) => (
          <Link
            key={idx}
            to="/kb"
            className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-stone-100 hover:bg-farm-100 text-stone-700 hover:text-farm-800 text-xs font-medium border border-stone-200 transition-colors"
          >
            <span className="font-mono text-[11px]">{src}</span>
            <ExternalLink className="w-3 h-3 text-stone-400" />
          </Link>
        ))}
      </div>
    </div>
  );
};
