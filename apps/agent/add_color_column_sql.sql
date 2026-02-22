-- Add color column to categories table
ALTER TABLE categories ADD COLUMN color TEXT DEFAULT '#3B82F6';

-- Update existing categories with appropriate colors
UPDATE categories SET color = CASE 
  WHEN name = 'Technology' THEN '#3B82F6'
  WHEN name = 'World News' THEN '#EF4444'
  WHEN name = 'Business & Finance' THEN '#10B981'
  WHEN name = 'Entertainment' THEN '#F59E0B'
  WHEN name = 'Sports' THEN '#8B5CF6'
  WHEN name = 'Science & Health' THEN '#06B6D4'
  WHEN name = 'Politics' THEN '#DC2626'
  WHEN name = 'Lifestyle' THEN '#EC4899'
  WHEN name = 'Environment' THEN '#059669'
  WHEN name = 'Education' THEN '#7C3AED'
  ELSE '#6B7280'
END;