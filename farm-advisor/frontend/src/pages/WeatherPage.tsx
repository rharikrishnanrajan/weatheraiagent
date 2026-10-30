import { useState, useEffect } from 'react';
import {
  Search,
  MapPin,
  Thermometer,
  Droplets,
  Wind,
  Gauge,
  Calendar,
  CloudSun,
} from 'lucide-react';
import { useFarmStore } from '../store/useFarmStore';
import { WeatherCard } from '../components/WeatherCard';
import { WeatherAlertBanner } from '../components/WeatherAlertBanner';
import { TempPrecipChart } from '../components/TempPrecipChart';

export const WeatherPage = () => {
  const { weather, loadWeather, profile } = useFarmStore();
  const [searchLocation, setSearchLocation] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (!weather) {
      loadWeather();
    }
  }, [weather, loadWeather]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchLocation.trim()) return;
    setIsSearching(true);
    await loadWeather({ place_name: searchLocation.trim() });
    setIsSearching(false);
  };

  const handleResetToProfile = async () => {
    if (profile?.latitude && profile?.longitude) {
      setSearchLocation('');
      await loadWeather({ lat: profile.latitude, lon: profile.longitude });
    }
  };

  if (!weather) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-stone-500">
        <div className="w-8 h-8 border-4 border-farm-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p>Loading live Open-Meteo meteorological data...</p>
      </div>
    );
  }

  const { current, location, daily, alerts } = weather;
  const total7DayRain = daily.reduce((acc, d) => acc + d.precipitation_sum, 0);
  const avgMaxTemp = daily.reduce((acc, d) => acc + d.temperature_2m_max, 0) / (daily.length || 1);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header & Location Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-farm-700 font-semibold text-xs tracking-wider uppercase mb-1">
            <CloudSun className="w-4 h-4" />
            <span>Open-Meteo Precision Agro-Forecast</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-stone-900 flex items-center space-x-2">
            <span>{location.name}</span>
            <span className="text-sm font-normal text-stone-500 hidden sm:inline">
              ({location.latitude.toFixed(2)}°N, {location.longitude.toFixed(2)}°W)
            </span>
          </h1>
        </div>

        {/* Search Bar */}
        <div className="flex items-center space-x-2">
          <form onSubmit={handleSearch} className="relative flex-1 sm:w-80">
            <input
              type="text"
              placeholder="Search town, city or region..."
              value={searchLocation}
              onChange={(e) => setSearchLocation(e.target.value)}
              disabled={isSearching}
              className="w-full pl-9 pr-16 py-2.5 rounded-xl border border-stone-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-farm-500 shadow-xs disabled:opacity-60"
            />
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-3.5" />
            <button
              type="submit"
              disabled={isSearching || !searchLocation.trim()}
              className="absolute right-1.5 top-1.5 px-2.5 py-1.5 rounded-lg bg-farm-600 hover:bg-farm-700 disabled:bg-stone-300 text-white text-xs font-semibold transition-colors"
            >
              {isSearching ? '...' : 'Find'}
            </button>
          </form>
          {profile && (
            <button
              onClick={handleResetToProfile}
              className="px-3 py-2.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-semibold border border-stone-200 transition-colors flex items-center space-x-1.5"
              title="Reset to your farm profile location"
            >
              <MapPin className="w-3.5 h-3.5 text-farm-600" />
              <span className="hidden sm:inline">Farm</span>
            </button>
          )}
        </div>
      </div>

      {/* Weather Hazard Alerts Banner */}
      <WeatherAlertBanner alerts={alerts} />

      {/* Top Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Current Temperature */}
        <div className="p-5 rounded-2xl bg-white border border-stone-200 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Thermometer className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-stone-500 uppercase">Current Temp</div>
            <div className="text-2xl font-black text-stone-900">
              {Math.round(current.temperature_2m)}°C
            </div>
            <div className="text-xs text-stone-500">
              Feels like {Math.round(current.apparent_temperature)}°C • {current.weather_description}
            </div>
          </div>
        </div>

        {/* Humidity & Dew Point */}
        <div className="p-5 rounded-2xl bg-white border border-stone-200 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Droplets className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-stone-500 uppercase">Relative Humidity</div>
            <div className="text-2xl font-black text-stone-900">
              {Math.round(current.relative_humidity_2m)}%
            </div>
            <div className="text-xs text-stone-500">
              {current.relative_humidity_2m > 80 ? 'Foliar disease watch' : 'Standard transpiration'}
            </div>
          </div>
        </div>

        {/* Wind Speed */}
        <div className="p-5 rounded-2xl bg-white border border-stone-200 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
            <Wind className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-stone-500 uppercase">Wind Velocity</div>
            <div className="text-2xl font-black text-stone-900">
              {Math.round(current.wind_speed_10m)} km/h
            </div>
            <div className="text-xs text-stone-500">
              Gusts up to {Math.round(current.wind_gusts_10m)} km/h
            </div>
          </div>
        </div>

        {/* 7-Day Cumulative Rain */}
        <div className="p-5 rounded-2xl bg-white border border-stone-200 shadow-xs flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center">
            <Gauge className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-semibold text-stone-500 uppercase">7-Day Rain Sum</div>
            <div className="text-2xl font-black text-stone-900">
              {total7DayRain.toFixed(1)} mm
            </div>
            <div className="text-xs text-stone-500">
              Avg High: {Math.round(avgMaxTemp)}°C
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Recharts Graph */}
      <TempPrecipChart daily={daily} />

      {/* 7-Day Daily Forecast Cards */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Calendar className="w-5 h-5 text-farm-600" />
          <h2 className="text-lg font-bold text-stone-900">7-Day Agronomic Daily Forecast</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {daily.map((item, idx) => (
            <WeatherCard key={item.date} item={item} isToday={idx === 0} />
          ))}
        </div>
      </div>
    </div>
  );
};
