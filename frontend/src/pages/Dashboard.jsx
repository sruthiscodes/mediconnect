import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { historyAPI } from '../services/api';
import { 
  Stethoscope, 
  History, 
  TrendingUp, 
  AlertTriangle,
  Calendar,
  ExternalLink
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import { clsx } from 'clsx';

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [recentHistory, setRecentHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [statsData, historyData] = await Promise.all([
          historyAPI.getUserStats(),
          historyAPI.getUserHistory(5)
        ]);
        
        setStats(statsData);
        setRecentHistory(historyData.logs);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return <LoadingSpinner size="lg" text="Loading dashboard..." />;
  }

  return (
    <div className="space-y-8">
      {/* Welcome section */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Welcome back, {user?.email?.split('@')[0]}!
            </h2>
            <p className="mt-1 text-gray-600">
              Ready to assess your health symptoms with AI-powered triage?
            </p>
          </div>
          <Link
            to="/triage"
            className="btn btn-primary flex items-center"
          >
            <Stethoscope className="h-5 w-5 mr-2" />
            Start Assessment
          </Link>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100">
                <TrendingUp className="h-6 w-6 text-primary-600" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Assessments</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats?.total_assessments || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-care-100">
                <Calendar className="h-6 w-6 text-care-600" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Recent Activity</p>
              <p className="text-2xl font-semibold text-gray-900">
                {stats?.recent_activity || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-yellow-100">
                <AlertTriangle className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Most Common</p>
              <p className="text-sm font-semibold text-gray-900">
                {stats?.most_common_urgency || 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent assessments */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Recent Assessments</h3>
          <Link
            to="/history"
            className="text-primary-600 hover:text-primary-500 font-medium text-sm flex items-center"
          >
            View all
            <ExternalLink className="h-4 w-4 ml-1" />
          </Link>
        </div>

        {recentHistory.length === 0 ? (
          <div className="text-center py-12">
            <Stethoscope className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h4 className="text-lg font-medium text-gray-900 mb-2">No assessments yet</h4>
            <p className="text-gray-600 mb-4">
              Start your first symptom assessment to track your health journey.
            </p>
            <Link to="/triage" className="btn btn-primary">
              Start Assessment
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {recentHistory.map((assessment) => (
              <div
                key={assessment.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:shadow-sm transition-shadow"
              >
                <div className="flex-1">
                  <p className="text-sm text-gray-900 mb-1">
                    {assessment.symptoms.length > 100 
                      ? `${assessment.symptoms.substring(0, 100)}...` 
                      : assessment.symptoms
                    }
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatDate(assessment.timestamp)}
                  </p>
                </div>
                <div className="ml-4">
                  <span
                    className={clsx(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
                      getUrgencyColor(assessment.urgency_level)
                    )}
                  >
                    {assessment.urgency_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link to="/triage" className="card hover:shadow-lg transition-shadow group">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 group-hover:bg-primary-200 transition-colors">
                <Stethoscope className="h-6 w-6 text-primary-600" />
              </div>
            </div>
            <div className="ml-4">
              <h4 className="text-lg font-medium text-gray-900">New Assessment</h4>
              <p className="text-sm text-gray-600">
                Describe your symptoms and get AI-powered triage recommendations
              </p>
            </div>
          </div>
        </Link>

        <Link to="/history" className="card hover:shadow-lg transition-shadow group">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-care-100 group-hover:bg-care-200 transition-colors">
                <History className="h-6 w-6 text-care-600" />
              </div>
            </div>
            <div className="ml-4">
              <h4 className="text-lg font-medium text-gray-900">View History</h4>
              <p className="text-sm text-gray-600">
                Review your past assessments and track health trends
              </p>
            </div>
          </div>
        </Link>
      </div>

      {/* Health disclaimer */}
      <div className="card border-yellow-200 bg-yellow-50">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
          </div>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-yellow-800">
              Important Health Disclaimer
            </h4>
            <p className="mt-1 text-sm text-yellow-700">
              This AI triage tool is for informational purposes only and should not replace professional medical advice. 
              Always consult with healthcare professionals for accurate diagnosis and treatment.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 