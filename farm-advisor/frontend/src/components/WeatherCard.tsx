import { Sun, Cloud, CloudSun, CloudRain, Droplets, Wind } from 'lucide-react';
import type { WeatherDailyItem } from '../types';

interface Props {
  item: WeatherDailyItem;
  isToday?: boolean;
}

export const WeatherCard = ({ item, isToday }: Props) => {
  const dateObj = new Date(item.date);
  const dayName = isToday
    ? 'Today'
    : dateObj.toLocaleDateString('en-US', { weekday: 'short' });
  const formattedDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const getWeatherIcon = (desc: string) => {
    const d = desc.toLowerCase();
    if (d.includes('rain') || d.includes('drizzle')) return <CloudRain className="w-7 h-7 text-blue-500" />;
    if (d.includes('overcast') || d.includes('cloudy')) return <Cloud className="w-7 h-7 text-stone-500" />;
    if (d.includes('partly')) return <CloudSun className="w-7 h-7 text-amber-500" />;
    return <Sun className="w-7 h-7 text-amber-500" />;
  };

  return (
    <div
      className={`p-4 rounded-2xl border transition-all flex flex-col justify-between ${
        isToday
          ? 'bg-farm-50/90 border-farm-300 shadow-sm ring-2 ring-farm-500/20'
          : 'bg-white border-stone-200 hover:border-farm-300 hover:shadow-xs'
      }`}
    >
      <div>
        <div className="flex items-center justify-between">
          <span className={`text-sm font-bold ${isToday ? 'text-farm-800' : 'text-stone-800'}`}>
            {dayName}
          </span>
          <span className="text-xs text-stone-500">{formattedDate}</span>
        </div>

        <div className="my-3 flex items-center justify-between">
          {getWeatherIcon(item.weather_description)}
          <div className="text-right">
            <div className="text-xl font-bold text-stone-900">
              {Math.round(item.temperature_2m_max)}°
            </div>
            <div className="text-xs text-stone-500">
              Low: {Math.round(item.temperature_2m_min)}°
            </div>
          </div>
        </div>

        <p className="text-xs text-stone-600 font-medium truncate mb-3" title={item.weather_description}>
          {item.weather_description}
        </p>
      </div>

      <div className="pt-2.5 border-t border-stone-100 space-y-1.5 text-xs text-stone-600">
        <div className="flex items-center justify-between">
          <span className="flex items-center space-x-1">
            <Droplets className="w-3.5 h-3.5 text-blue-500" />
            <span>Rain</span>
          </span>
          <span className="font-semibold text-stone-800">
            {item.precipitation_sum.toFixed(1)} mm
            {item.precipitation_probability_max !== undefined && (
              <span className="text-[11px] text-blue-600 ml-1">({item.precipitation_probability_max}%)</span>
            )}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="flex items-center space-x-1">
            <Wind className="w-3.5 h-3.5 text-stone-400" />
            <span>Wind</span>
          </span>
          <span className="font-semibold text-stone-800">{Math.round(item.wind_speed_10m_max)} km/h</span>
        </div>

        {item.et0_fao_evapotranspiration !== undefined && (
          <div className="flex items-center justify-between text-[11px] text-stone-500">
            <span>ET₀ Demand</span>
            <span className="font-medium text-farm-700">{item.et0_fao_evapotranspiration.toFixed(1)} mm</span>
          </div>
        )}
      </div>
    </div>
  );
};
