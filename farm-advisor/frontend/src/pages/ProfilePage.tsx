import { useState, useEffect } from 'react';
import {
  User,
  MapPin,
  Layers,
  Droplet,
  Save,
  CheckCircle2,
  AlertCircle,
  Search,
  Plus,
  X,
} from 'lucide-react';
import { useFarmStore } from '../store/useFarmStore';
import type { FarmProfile } from '../types';

const COMMON_CROPS = ['Tomato', 'Corn', 'Wheat', 'Potato', 'Rice', 'Soybean', 'Cotton', 'Onion'];
const SOIL_TYPES = ['Sandy', 'Loamy', 'Clay', 'Silt', 'Peat'];
const IRRIGATION_TYPES = ['Drip', 'Sprinkler', 'Flood', 'Rainfed'];

export const ProfilePage = () => {
  const { profile, loadProfile, saveProfile } = useFarmStore();

  const [formData, setFormData] = useState<Partial<FarmProfile>>({
    farmer_name: '',
    location_name: '',
    latitude: 0,
    longitude: 0,
    crops: [],
    field_size_hectares: 10,
    soil_type: 'Loamy',
    irrigation_type: 'Drip',
    preferred_language: 'en',
    notes: '',
  });

  const [newCropInput, setNewCropInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    if (profile) {
      setFormData(profile);
    }
  }, [profile]);

  const handleLookupCoordinates = async () => {
    if (!formData.location_name?.trim()) return;
    setGeoError(null);
    try {
      const res = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(
          formData.location_name
        )}&count=1&format=json`
      );
      const data = await res.json();
      if (data.results && data.results.length > 0) {
        const top = data.results[0];
        setFormData((prev) => ({
          ...prev,
          latitude: top.latitude,
          longitude: top.longitude,
          location_name: `${top.name}${top.admin1 ? ', ' + top.admin1 : ''}${
            top.country ? ', ' + top.country : ''
          }`,
        }));
      } else {
        setGeoError('Could not locate place. Please enter coordinates manually.');
      }
    } catch {
      setGeoError('Geocoding request failed. Check internet connectivity.');
    }
  };

  const handleToggleCrop = (crop: string) => {
    const current = formData.crops || [];
    if (current.includes(crop)) {
      setFormData({ ...formData, crops: current.filter((c) => c !== crop) });
    } else {
      setFormData({ ...formData, crops: [...current, crop] });
    }
  };

  const handleAddCustomCrop = () => {
    const trimmed = newCropInput.trim();
    if (!trimmed) return;
    const current = formData.crops || [];
    if (!current.includes(trimmed)) {
      setFormData({ ...formData, crops: [...current, trimmed] });
    }
    setNewCropInput('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMessage(null);
    try {
      await saveProfile(formData);
      setSuccessMessage('Farm Profile successfully saved and synchronized!');
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-stone-900">Farm Profile & Soil Settings</h1>
        <p className="text-sm text-stone-500 mt-1">
          Configure your crops, coordinates, soil characteristics, and irrigation method. AgriPulse uses these settings to personalize all agronomic recommendations.
        </p>
      </div>

      {successMessage && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center space-x-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <span className="font-semibold">{successMessage}</span>
        </div>
      )}

      {geoError && (
        <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm flex items-center space-x-2">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <span>{geoError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Farmer Info */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-stone-900 flex items-center space-x-2">
            <User className="w-4 h-4 text-farm-600" />
            <span>Grower & Farm Identity</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Farmer or Enterprise Name
              </label>
              <input
                type="text"
                value={formData.farmer_name || ''}
                onChange={(e) => setFormData({ ...formData, farmer_name: e.target.value })}
                className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Total Field Size (Hectares)
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                value={formData.field_size_hectares || 10}
                onChange={(e) =>
                  setFormData({ ...formData, field_size_hectares: parseFloat(e.target.value) || 1 })
                }
                className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none"
                required
              />
            </div>
          </div>
        </div>

        {/* Location & GPS */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-stone-900 flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-farm-600" />
            <span>Farm Geographic Location</span>
          </h2>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">
              Farm Location or City Name
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                placeholder="e.g. Sacramento, California or Fresno, CA"
                value={formData.location_name || ''}
                onChange={(e) => setFormData({ ...formData, location_name: e.target.value })}
                className="flex-1 px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none"
                required
              />
              <button
                type="button"
                onClick={handleLookupCoordinates}
                className="px-4 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
              >
                <Search className="w-3.5 h-3.5" />
                <span>Lookup GPS</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Latitude</label>
              <input
                type="number"
                step="0.0001"
                value={formData.latitude || 0}
                onChange={(e) =>
                  setFormData({ ...formData, latitude: parseFloat(e.target.value) || 0 })
                }
                className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none font-mono"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Longitude</label>
              <input
                type="number"
                step="0.0001"
                value={formData.longitude || 0}
                onChange={(e) =>
                  setFormData({ ...formData, longitude: parseFloat(e.target.value) || 0 })
                }
                className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none font-mono"
                required
              />
            </div>
          </div>
        </div>

        {/* Crops Grown */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-stone-900 flex items-center space-x-2">
            <Layers className="w-4 h-4 text-farm-600" />
            <span>Crops Grown in Field</span>
          </h2>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-2">
              Select or Toggle Major Crops
            </label>
            <div className="flex flex-wrap gap-2">
              {COMMON_CROPS.map((c) => {
                const isSelected = (formData.crops || []).includes(c);
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => handleToggleCrop(c)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                      isSelected
                        ? 'bg-farm-600 text-white border-farm-600 shadow-xs'
                        : 'bg-stone-50 text-stone-700 border-stone-200 hover:border-farm-300'
                    }`}
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">
              Add Custom or Specialized Crop
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                placeholder="e.g. Alfalfa, Grapes, Almonds"
                value={newCropInput}
                onChange={(e) => setNewCropInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCustomCrop())}
                className="flex-1 px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={handleAddCustomCrop}
                className="px-4 py-2 rounded-xl bg-farm-600 hover:bg-farm-700 text-white text-xs font-semibold flex items-center space-x-1.5 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Crop</span>
              </button>
            </div>
          </div>

          {/* Selected Crops Tags */}
          <div className="pt-2">
            <span className="text-xs text-stone-500 block mb-1.5 font-medium">Currently Selected Crops:</span>
            <div className="flex flex-wrap gap-1.5">
              {(formData.crops || []).map((c) => (
                <span
                  key={c}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-farm-50 text-farm-800 text-xs font-semibold border border-farm-200"
                >
                  <span>{c}</span>
                  <button
                    type="button"
                    onClick={() => handleToggleCrop(c)}
                    className="hover:text-red-600 ml-1"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Soil & Irrigation */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-stone-900 flex items-center space-x-2">
            <Droplet className="w-4 h-4 text-farm-600" />
            <span>Soil Type & Irrigation Infrastructure</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Predominant Soil Classification
              </label>
              <select
                value={formData.soil_type || 'Loamy'}
                onChange={(e) => setFormData({ ...formData, soil_type: e.target.value })}
                className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none bg-white"
              >
                {SOIL_TYPES.map((s) => (
                  <option key={s} value={s}>
                    {s} Soil
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">
                Primary Irrigation System
              </label>
              <select
                value={formData.irrigation_type || 'Drip'}
                onChange={(e) => setFormData({ ...formData, irrigation_type: e.target.value })}
                className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none bg-white"
              >
                {IRRIGATION_TYPES.map((i) => (
                  <option key={i} value={i}>
                    {i} Irrigation
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">
              Advisory Notes & Historical Practices
            </label>
            <textarea
              rows={3}
              value={formData.notes || ''}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="e.g. Organic certified, drip lines at 30 cm depth, historical fungal pressure in late autumn..."
              className="w-full px-3.5 py-2 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center space-x-2 px-6 py-3 rounded-xl bg-farm-600 hover:bg-farm-700 disabled:bg-stone-300 text-white font-bold text-sm shadow-xs transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>{isSaving ? 'Saving Profile...' : 'Save & Sync Farm Profile'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
