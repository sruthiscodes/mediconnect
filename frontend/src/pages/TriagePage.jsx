import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { triageAPI } from '../services/api';
import { 
  Stethoscope, 
  AlertTriangle, 
  CheckCircle, 
  ExternalLink,
  RefreshCw,
  Clock
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';

const TriagePage = () => {
  const [symptoms, setSymptoms] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!symptoms.trim()) {
      toast.error('Please describe your symptoms');
      return;
    }

    setLoading(true);
    
    try {
      const response = await triageAPI.assessSymptoms(symptoms.trim());
      setResult(response.data);
      toast.success('Assessment completed!');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSymptoms('');
    setResult(null);
  };

  const getUrgencyColor = (urgencyLevel) => {
    const colors = {
      'Emergency': 'urgency-emergency',
      'Urgent': 'urgency-urgent', 
      'Primary Care': 'urgency-primary-care',
      'Telehealth': 'urgency-telehealth',
      'Self-Care': 'urgency-self-care',
    };
    return colors[urgencyLevel] || 'bg-gray-50 text-gray-700 border-gray-200';
  };

  const getUrgencyIcon = (urgencyLevel) => {
    if (urgencyLevel === 'Emergency') {
      return <AlertTriangle className="h-6 w-6 text-emergency-600" />;
    }
    return <CheckCircle className="h-6 w-6 text-care-600" />;
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          AI-Powered Symptom Assessment
        </h2>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Describe your symptoms in detail and get personalized triage recommendations 
          powered by artificial intelligence and clinical guidelines.
        </p>
      </div>

      {!result ? (
        /* Input form */
        <div className="card max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="symptoms" className="block text-sm font-medium text-gray-700 mb-3">
                Describe Your Symptoms
              </label>
              <textarea
                id="symptoms"
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
                className="form-textarea min-h-32"
                placeholder="Please describe your symptoms as specifically as possible. Include details like:&#10;• When did they start?&#10;• How severe are they (1-10)?&#10;• What makes them better or worse?&#10;• Any associated symptoms?&#10;&#10;Example: 'I have chest pain that started 2 hours ago, feels like pressure, 7/10 severity, gets worse when I breathe deeply, also feeling dizzy and nauseous.'"
                required
                disabled={loading}
              />
              <p className="mt-2 text-sm text-gray-500">
                Be as detailed as possible for the most accurate assessment.
              </p>
            </div>

            <div className="flex items-center justify-between">
              <button
                type="submit"
                disabled={loading || !symptoms.trim()}
                className="btn btn-primary flex items-center"
              >
                {loading ? (
                  <>
                    <LoadingSpinner size="sm" text="" />
                    <span className="ml-2">Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Stethoscope className="h-5 w-5 mr-2" />
                    Get Assessment
                  </>
                )}
              </button>
              
              <p className="text-sm text-gray-500">
                <Clock className="h-4 w-4 inline mr-1" />
                Usually takes 5-10 seconds
              </p>
            </div>
          </form>

          {/* Sample symptoms */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">Sample symptoms to try:</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                "I have a mild headache and feel tired",
                "Chest pain and feeling dizzy",
                "High fever and severe headache",
                "Persistent cough with blood"
              ].map((sample, index) => (
                <button
                  key={index}
                  onClick={() => setSymptoms(sample)}
                  className="text-left p-3 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                  disabled={loading}
                >
                  "{sample}"
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Results */
        <div className="space-y-6">
          {/* Assessment result card */}
          <div className="card">
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center">
                {getUrgencyIcon(result.urgency_level)}
                <h3 className="text-xl font-semibold text-gray-900 ml-3">
                  Assessment Complete
                </h3>
              </div>
              <span className="text-sm text-gray-500">
                {formatTimestamp(result.timestamp)}
              </span>
            </div>

            {/* Urgency level */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Recommended Urgency Level
              </label>
              <span
                className={clsx(
                  'inline-flex items-center px-4 py-2 rounded-lg text-lg font-medium border',
                  getUrgencyColor(result.urgency_level)
                )}
              >
                {result.urgency_level}
              </span>
            </div>

            {/* Symptoms reviewed */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Symptoms Reviewed
              </label>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-900">{symptoms}</p>
              </div>
            </div>

            {/* Explanation */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                AI Assessment & Explanation
              </label>
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-gray-900">{result.explanation}</p>
              </div>
            </div>

            {/* Next steps */}
            {result.next_steps && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Recommended Next Steps
                </label>
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-medium text-gray-900">
                      {result.next_steps.action}
                    </h4>
                    <span className="text-sm text-gray-500">
                      {result.next_steps.timeframe}
                    </span>
                  </div>
                  <p className="text-gray-600 mb-4">
                    {result.next_steps.additional_info}
                  </p>
                  
                  {result.next_steps.booking_url && result.next_steps.booking_url !== '#emergency' && result.next_steps.booking_url !== '#self-care' && (
                    <a
                      href={result.next_steps.booking_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-primary flex items-center w-fit"
                    >
                      Book Care Appointment
                      <ExternalLink className="h-4 w-4 ml-2" />
                    </a>
                  )}
                  
                  {result.urgency_level === 'Emergency' && (
                    <div className="bg-emergency-50 border border-emergency-200 rounded-lg p-4 mt-4">
                      <div className="flex items-center">
                        <AlertTriangle className="h-5 w-5 text-emergency-600 mr-2" />
                        <span className="font-medium text-emergency-800">
                          Emergency Situation Detected
                        </span>
                      </div>
                      <p className="text-emergency-700 text-sm mt-1">
                        Please call 911 or go to the nearest emergency room immediately.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-between">
            <button
              onClick={handleReset}
              className="btn btn-secondary flex items-center"
            >
              <RefreshCw className="h-5 w-5 mr-2" />
              New Assessment
            </button>
            
            <Link
              to="/history"
              className="text-primary-600 hover:text-primary-500 font-medium flex items-center"
            >
              View Assessment History
              <ExternalLink className="h-4 w-4 ml-1" />
            </Link>
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="card border-yellow-200 bg-yellow-50 max-w-2xl mx-auto">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-yellow-800">
              Medical Disclaimer
            </h4>
            <p className="mt-1 text-sm text-yellow-700">
              This tool provides preliminary guidance only. It cannot replace professional medical 
              evaluation. In case of emergency, call 911 immediately. For urgent concerns, 
              contact your healthcare provider or visit an emergency room.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TriagePage; 