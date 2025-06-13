import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { historyAPI } from '../services/api';
import { 
  History, 
  Stethoscope, 
  Calendar, 
  Filter,
  Search,
  AlertTriangle,
  TrendingUp,
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import { clsx } from 'clsx';

const HistoryPage = () => {
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterLevel, setFilterLevel] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [historyData, statsData] = await Promise.all([
          historyAPI.getUserHistory(50),
          historyAPI.getUserStats()
        ]);
        
        // Handle different response formats
        const logs = historyData.logs || historyData || [];
        setHistory(logs);
        setStats(statsData);
      } catch (error) {
        console.error('Failed to fetch history:', error);
        // Set empty arrays on error to prevent crashes
        setHistory([]);
        setStats(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

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

  const getResolutionStatus = (status) => {
    const statusConfig = {
      'Resolved': { 
        color: 'text-green-600 bg-green-50 border-green-200', 
        icon: CheckCircle,
        label: 'Resolved'
      },
      'Improved': { 
        color: 'text-blue-600 bg-blue-50 border-blue-200', 
        icon: TrendingUp,
        label: 'Improved'
      },
      'Ongoing': { 
        color: 'text-yellow-600 bg-yellow-50 border-yellow-200', 
        icon: Clock,
        label: 'Ongoing'
      },
      'Worsened': { 
        color: 'text-red-600 bg-red-50 border-red-200', 
        icon: AlertCircle,
        label: 'Worsened'
      },
      'Unknown': { 
        color: 'text-gray-600 bg-gray-50 border-gray-200', 
        icon: XCircle,
        label: 'Unknown'
      }
    };
    return statusConfig[status] || statusConfig['Unknown'];
  };

  const updateResolutionStatus = async (symptomLogId, newStatus) => {
    try {
      await historyAPI.updateResolutionStatus(symptomLogId, newStatus);
      // Refresh the history
      const [historyData, statsData] = await Promise.all([
        historyAPI.getUserHistory(50),
        historyAPI.getUserStats()
      ]);
      
      const logs = historyData.logs || historyData || [];
      setHistory(logs);
      setStats(statsData);
    } catch (error) {
      console.error('Failed to update resolution status:', error);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredHistory = history.filter(item => {
    const matchesSearch = item.symptoms.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.explanation.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterLevel === 'all' || item.urgency_level === filterLevel;
    
    return matchesSearch && matchesFilter;
  });

  const urgencyLevels = ['Emergency', 'Urgent', 'Primary Care', 'Telehealth', 'Self-Care'];

  if (loading) {
    return <LoadingSpinner size="lg" text="Loading history..." />;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Assessment History</h2>
          <p className="mt-1 text-gray-600">
            Review your past symptom assessments and health trends
          </p>
        </div>
        <Link to="/triage" className="btn btn-primary flex items-center">
          <Stethoscope className="h-5 w-5 mr-2" />
          New Assessment
        </Link>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100">
                  <TrendingUp className="h-5 w-5 text-primary-600" />
                </div>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Total</p>
                <p className="text-xl font-semibold text-gray-900">
                  {stats.total_assessments}
                </p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emergency-100">
                  <AlertTriangle className="h-5 w-5 text-emergency-600" />
                </div>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Emergency</p>
                <p className="text-xl font-semibold text-gray-900">
                  {stats.urgency_distribution?.Emergency || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-urgent-100">
                  <Calendar className="h-5 w-5 text-urgent-600" />
                </div>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Urgent</p>
                <p className="text-xl font-semibold text-gray-900">
                  {stats.urgency_distribution?.Urgent || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-care-100">
                  <History className="h-5 w-5 text-care-600" />
                </div>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Self-Care</p>
                <p className="text-xl font-semibold text-gray-900">
                  {stats.urgency_distribution?.['Self-Care'] || 0}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="form-input pl-10"
                placeholder="Search symptoms or explanations..."
              />
            </div>
          </div>

          {/* Filter by urgency level */}
          <div className="sm:w-48">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Filter className="h-5 w-5 text-gray-400" />
              </div>
              <select
                value={filterLevel}
                onChange={(e) => setFilterLevel(e.target.value)}
                className="form-input pl-10"
              >
                <option value="all">All Levels</option>
                {urgencyLevels.map(level => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* History List */}
      <div className="card">
        {filteredHistory.length === 0 ? (
          <div className="text-center py-12">
            <History className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {history.length === 0 ? 'No assessments yet' : 'No matching assessments'}
            </h3>
            <p className="text-gray-600 mb-4">
              {history.length === 0 
                ? 'Start your first symptom assessment to build your health history.'
                : 'Try adjusting your search or filter criteria.'
              }
            </p>
            {history.length === 0 && (
              <Link to="/triage" className="btn btn-primary">
                Start Assessment
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {filteredHistory.length} Assessment{filteredHistory.length !== 1 ? 's' : ''}
              </h3>
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear search
                </button>
              )}
            </div>

            {filteredHistory.map((assessment) => {
              const resolutionConfig = getResolutionStatus(assessment.resolution_status || 'Unknown');
              const ResolutionIcon = resolutionConfig.icon;
              
              return (
                <div
                  key={assessment.id}
                  className="border border-gray-200 rounded-lg p-6 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <span
                        className={clsx(
                          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
                          getUrgencyColor(assessment.urgency_level)
                        )}
                      >
                        {assessment.urgency_level}
                      </span>
                      
                      <span
                        className={clsx(
                          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
                          resolutionConfig.color
                        )}
                      >
                        <ResolutionIcon className="h-3 w-3 mr-1" />
                        {resolutionConfig.label}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500">
                      {formatDate(assessment.timestamp)}
                    </span>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Symptoms</h4>
                      <p className="text-gray-900">{assessment.symptoms}</p>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">AI Assessment</h4>
                      <p className="text-gray-900">{assessment.explanation}</p>
                    </div>

                    {assessment.confidence && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Confidence Score</h4>
                        <div className="flex items-center">
                          <div className="w-32 bg-gray-200 rounded-full h-2 mr-3">
                            <div
                              className="bg-primary-600 h-2 rounded-full"
                              style={{ width: `${assessment.confidence * 100}%` }}
                            ></div>
                          </div>
                          <span className="text-sm text-gray-600">
                            {Math.round(assessment.confidence * 100)}%
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Resolution Status Update */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Update Status</h4>
                      <div className="flex space-x-2">
                        {['Resolved', 'Improved', 'Ongoing', 'Worsened'].map((status) => (
                          <button
                            key={status}
                            onClick={() => updateResolutionStatus(assessment.id, status)}
                            className={clsx(
                              'px-3 py-1 text-xs rounded-full border transition-colors',
                              assessment.resolution_status === status
                                ? getResolutionStatus(status).color
                                : 'text-gray-600 bg-gray-50 border-gray-200 hover:bg-gray-100'
                            )}
                          >
                            {status}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Health trends note */}
      {stats && stats.total_assessments > 0 && (
        <div className="card border-blue-200 bg-blue-50">
          <div className="flex">
            <div className="flex-shrink-0">
              <TrendingUp className="h-5 w-5 text-blue-600" />
            </div>
            <div className="ml-3">
              <h4 className="text-sm font-medium text-blue-800">
                Health Insights
              </h4>
              <div className="mt-1 text-sm text-blue-700">
                <p>Most common urgency level: <strong>{stats.most_common_urgency || 'N/A'}</strong></p>
                <p className="mt-1">
                  Keep tracking your symptoms to identify patterns and better understand your health needs.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryPage;