"""
Blog Writer Crew with Hierarchical Memory Access.

This crew demonstrates how to use the hierarchical memory tool to:
1. Access blog writing procedures from synth_class templates
2. Follow established SOPs
3. Create blog content with proper memory tracking
"""
from typing import Dict, Any, List
from uuid import UUID
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew

import logging
logger = logging.getLogger(__name__)

from services.crew_api.src.tools import (
    create_hierarchical_memory_tool,
    HierarchicalMemoryConfig
)

@CrewBase
class BlogWriterHierarchicalCrew:
    """Blog writer crew that uses hierarchical memory for procedures."""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(self, synth_id: UUID, client_id: UUID):
        """Initialize with actor context for memory tool."""
        self.synth_id = synth_id
        self.client_id = client_id
        
        # Create hierarchical memory tool for this synth
        self.memory_tool = create_hierarchical_memory_tool(
            actor_type="synth",
            actor_id=synth_id,
            client_id=client_id,
            config=HierarchicalMemoryConfig(
                enable_hierarchy=True,
                include_synth_class=True,
                include_client=False,
                enable_cross_context=True
            )
        )
    
    @agent
    def procedure_researcher(self) -> Agent:
        """Agent responsible for finding and understanding procedures."""
        return Agent(
            role="Procedure Research Specialist",
            goal="Find and analyze the most relevant procedures and templates for the task",
            backstory="""You are an expert at navigating organizational knowledge. 
            You specialize in finding SOPs, templates, and guidelines from the 
            synth_class templates. You understand the importance of following 
            established procedures for consistency and quality.""",
            tools=[self.memory_tool],
            verbose=True,
            memory=True
        )
    
    @agent
    def blog_writer(self) -> Agent:
        """Agent responsible for writing blog content following procedures."""
        return Agent(
            role="SEO Blog Writer",
            goal="Create high-quality, SEO-optimized blog posts following established procedures",
            backstory="""You are a skilled blog writer who excels at creating 
            engaging content. You always follow the established SOPs and procedures 
            to ensure consistency and quality. You understand SEO principles and 
            apply them naturally in your writing.""",
            tools=[self.memory_tool],
            verbose=True,
            memory=True
        )
    
    @agent
    def quality_checker(self) -> Agent:
        """Agent responsible for quality assurance and memory tracking."""
        return Agent(
            role="Quality Assurance Specialist",
            goal="Ensure blog posts meet quality standards and track performance",
            backstory="""You are meticulous about quality and compliance. You check 
            that all procedures were followed correctly, ensure quality standards 
            are met, and create proper memory records for future reference.""",
            tools=[self.memory_tool],
            verbose=True,
            memory=True
        )
    
    @task
    def find_procedures_task(self) -> Task:
        """Task to find relevant blog writing procedures."""
        return Task(
            description="""
            Search for blog writing procedures and templates from the synth_class memory.
            
            Steps:
            1. Use search_templates to find blog writing SOPs
            2. Use search_hierarchical to find any additional guidelines
            3. Identify the specific phases and steps in the procedures
            4. Note any quality checklists or requirements
            
            Focus on:
            - Blog Writing Standard Operating Procedures
            - SEO optimization guidelines
            - Quality checklists
            - Content structure templates
            
            Provide a structured summary of all procedures found.
            """,
            agent=self.procedure_researcher(),
            expected_output="Structured list of procedures with phases and key requirements"
        )
    
    @task
    def write_blog_task(self) -> Task:
        """Task to write blog following procedures."""
        return Task(
            description="""
            Write a blog post about '{topic}' following the procedures found.
            
            Requirements:
            1. Follow each phase of the blog writing SOP
            2. Implement all required steps from the procedure
            3. Apply SEO optimization techniques as specified
            4. Meet the quality standards defined in the procedures
            
            Create a memory entity for the blog post with:
            - Name: The blog title
            - Type: "content_output"
            - Metadata: Include word count, SEO score, time taken, phases completed
            
            The blog should be 800-1500 words as specified in the procedures.
            """,
            agent=self.blog_writer(),
            expected_output="Complete blog post with title, content, and metadata",
            context=[self.find_procedures_task()]
        )
    
    @task
    def quality_check_task(self) -> Task:
        """Task to check quality and create memory records."""
        return Task(
            description="""
            Perform quality checks and create proper memory records.
            
            Steps:
            1. Search for quality checklists in the templates
            2. Check the blog against each quality criterion
            3. Calculate quality scores for each category
            4. Create observations about the blog creation process
            5. Create a relationship between the blog and the SOP followed
            
            Memory operations needed:
            - Add observations about quality scores
            - Add observations about what worked well
            - Create relationship: blog "followed_procedure" SOP
            - Note any deviations or improvements made
            
            Provide a quality report with scores and recommendations.
            """,
            agent=self.quality_checker(),
            expected_output="Quality assessment report with scores and memory records created",
            context=[self.find_procedures_task(), self.write_blog_task()]
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the blog writer crew with hierarchical memory."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
            cache=True,
            max_rpm=10
        )

def create_blog_writer_crew(
    synth_id: UUID,
    client_id: UUID,
    topic: str
) -> Dict[str, Any]:
    """
    Create and run a blog writer crew with hierarchical memory.
    
    Args:
        synth_id: The synth's ID (should be based on synth_class 24)
        client_id: The client ID
        topic: The blog topic to write about
    
    Returns:
        The crew execution results
    """
    # Create crew instance
    crew_instance = BlogWriterHierarchicalCrew(synth_id, client_id)
    
    # Update task descriptions with topic
    crew_instance.tasks[1].description = crew_instance.tasks[1].description.format(
        topic=topic
    )
    
    # Run the crew
    result = crew_instance.crew().kickoff()
    
    return {
        "success": True,
        "topic": topic,
        "result": result,
        "phases_completed": ["research", "writing", "quality_check"]
    }

# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Example IDs (replace with real ones)
    SYNTH_ID = UUID("660e8400-e29b-41d4-a716-446655440001")  # Should be synth_class 24
    CLIENT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
    
    # Create and run crew
    result = create_blog_writer_crew(
        synth_id=SYNTH_ID,
        client_id=CLIENT_ID,
        topic="10 Python Decorators Every Developer Should Know"
    )
    
    logger.info(f"Blog creation result: {result}")