import { AlertTriangle, Snowflake, Flame, CloudRain, Wind, AlertCircle } from 'lucide-react';
import type { WeatherAlert } from '../types';

interface Props {
  alerts: WeatherAlert[];
}

export const WeatherAlertBanner = ({ alerts }: Props) => {
  if (!alerts || alerts.length === 0) return null;

  const getAlertIcon = (category: string) => {
    const catLower = category.toLowerCase();
    if (catLower.includes('frost')) return <Snowflake className="w-5 h-5 text-blue-600 flex-shrink-0" />;
    if (catLower.includes('heat')) return <Flame className="w-5 h-5 text-amber-600 flex-shrink-0" />;
    if (catLower.includes('rain') || catLower.includes('flood')) return <CloudRain className="w-5 h-5 text-indigo-600 flex-shrink-0" />;
    if (catLower.includes('wind')) return <Wind className="w-5 h-5 text-teal-600 flex-shrink-0" />;
    return <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />;
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'severe':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'moderate':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      default:
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    }
  };

  return (
    <div className="space-y-3 mb-6">
      {alerts.map((alert, idx) => (
        <div
          key={idx}
          className="p-4 rounded-xl border border-red-200 bg-red-50/70 shadow-sm flex flex-col sm:flex-row sm:items-start justify-between gap-3"
        >
          <div className="flex items-start space-x-3">
            <div className="p-2 rounded-lg bg-white shadow-xs">
              {getAlertIcon(alert.category)}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${getSeverityBadge(alert.severity)}`}>
                  {alert.severity.toUpperCase()}
                </span>
                <h4 className="text-sm font-bold text-stone-900">{alert.title}</h4>
                {alert.valid_time && (
                  <span className="text-xs text-stone-500 hidden md:inline">({alert.valid_time})</span>
                )}
              </div>
              <p className="text-xs text-stone-700 mt-1">{alert.description}</p>
              <div className="mt-2 text-xs font-semibold text-red-900 bg-red-100/60 p-2 rounded-lg border border-red-200/60 flex items-center space-x-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-red-700 flex-shrink-0" />
                <span>Action: {alert.action_recommendation}</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
