-- MediConnect Supabase Schema
-- Run this in your Supabase SQL editor to set up the required tables

-- Enable Row Level Security
ALTER DATABASE postgres SET "app.jwt_secret" TO 'your-jwt-secret-here';

-- Create symptom_logs table
CREATE TABLE IF NOT EXISTS public.symptom_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    symptoms TEXT NOT NULL,
    urgency_level TEXT NOT NULL CHECK (urgency_level IN ('Emergency', 'Urgent', 'Primary Care', 'Telehealth', 'Self-Care')),
    explanation TEXT NOT NULL,
    confidence DECIMAL(3,2),
    esi_classification TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add esi_classification column if it doesn't exist (for existing databases)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'symptom_logs' 
                   AND column_name = 'esi_classification') THEN
        ALTER TABLE public.symptom_logs ADD COLUMN esi_classification TEXT;
    END IF;
END $$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_symptom_logs_user_id ON public.symptom_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_created_at ON public.symptom_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_urgency_level ON public.symptom_logs(urgency_level);

-- Enable Row Level Security
ALTER TABLE public.symptom_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Users can only see their own symptom logs
CREATE POLICY "Users can view their own symptom logs" ON public.symptom_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Users can insert their own symptom logs
CREATE POLICY "Users can insert their own symptom logs" ON public.symptom_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can update their own symptom logs
CREATE POLICY "Users can update their own symptom logs" ON public.symptom_logs
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Users can delete their own symptom logs
CREATE POLICY "Users can delete their own symptom logs" ON public.symptom_logs
    FOR DELETE USING (auth.uid() = user_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON public.symptom_logs
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Create a view for symptom statistics (optional)
CREATE OR REPLACE VIEW public.user_symptom_stats AS
SELECT 
    user_id,
    COUNT(*) as total_assessments,
    COUNT(CASE WHEN urgency_level = 'Emergency' THEN 1 END) as emergency_count,
    COUNT(CASE WHEN urgency_level = 'Urgent' THEN 1 END) as urgent_count,
    COUNT(CASE WHEN urgency_level = 'Primary Care' THEN 1 END) as primary_care_count,
    COUNT(CASE WHEN urgency_level = 'Telehealth' THEN 1 END) as telehealth_count,
    COUNT(CASE WHEN urgency_level = 'Self-Care' THEN 1 END) as self_care_count,
    MIN(created_at) as first_assessment,
    MAX(created_at) as last_assessment
FROM public.symptom_logs
GROUP BY user_id;

-- Grant access to the stats view
ALTER VIEW public.user_symptom_stats OWNER TO postgres;
CREATE POLICY "Users can view their own stats" ON public.user_symptom_stats
    FOR SELECT USING (auth.uid() = user_id);

-- Create function for getting recent symptoms (for RAG context)
CREATE OR REPLACE FUNCTION public.get_user_recent_symptoms(p_user_id UUID, p_limit INTEGER DEFAULT 5)
RETURNS TABLE(symptoms TEXT, created_at TIMESTAMP WITH TIME ZONE) AS $$
BEGIN
    RETURN QUERY
    SELECT s.symptoms, s.created_at
    FROM public.symptom_logs s
    WHERE s.user_id = p_user_id
    ORDER BY s.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on the function
GRANT EXECUTE ON FUNCTION public.get_user_recent_symptoms TO authenticated;

COMMENT ON TABLE public.symptom_logs IS 'Stores user symptom assessments and triage results';
COMMENT ON COLUMN public.symptom_logs.symptoms IS 'User-entered symptom description';
COMMENT ON COLUMN public.symptom_logs.urgency_level IS 'AI-determined urgency level';
COMMENT ON COLUMN public.symptom_logs.explanation IS 'AI-generated explanation and recommendations';
COMMENT ON COLUMN public.symptom_logs.confidence IS 'AI confidence score (0.0 to 1.0)';

-- Insert some sample data for testing (optional)
-- Note: Replace with actual user UUID after user signup
/*
INSERT INTO public.symptom_logs (user_id, symptoms, urgency_level, explanation, confidence) VALUES
(
    '00000000-0000-0000-0000-000000000000', -- Replace with real user ID
    'I have a mild headache and feel tired',
    'Self-Care',
    'Your symptoms suggest fatigue and mild headache which can often be managed with rest, hydration, and over-the-counter pain relief. Monitor symptoms and seek care if they worsen.',
    0.85
);
*/ 