"""
Models employment impacts of solar deployment, including job creation (direct, indirect, induced),
workforce development pathways, and gender & diversity inclusion.
"""

class EmploymentModel:
    """A class to model socioeconomic impacts related to employment."""
    def __init__(self, regional_employment_data: dict):
        """
        Initializes with regional employment baselines and job creation factors.
        regional_employment_data: e.g., {'RegionX': {'solar_jobs_per_mw': 10}}
        """
        self.regional_employment_data = regional_employment_data
        print(f"EmploymentModel initialized.")

    def estimate_job_creation(self, region: str, new_solar_capacity_mw: float) -> dict:
        """Estimates direct, indirect, and induced jobs from new solar capacity."""
        region_data = self.regional_employment_data.get(region, {})
        jobs_per_mw_direct = region_data.get('solar_jobs_per_mw_direct', 5) # Default
        indirect_multiplier = region_data.get('indirect_multiplier', 1.5) # e.g., 1.5 indirect jobs per direct job
        induced_multiplier = region_data.get('induced_multiplier', 0.75) # e.g., 0.75 induced jobs per direct job

        direct_jobs = new_solar_capacity_mw * jobs_per_mw_direct
        indirect_jobs = direct_jobs * indirect_multiplier
        induced_jobs = direct_jobs * induced_multiplier
        total_jobs = direct_jobs + indirect_jobs + induced_jobs

        print(f"Job creation in {region} for {new_solar_capacity_mw} MW solar:")
        print(f"  Direct Jobs: {direct_jobs:.0f}")
        print(f"  Indirect Jobs: {indirect_jobs:.0f}")
        print(f"  Induced Jobs: {induced_jobs:.0f}")
        print(f"  Total Jobs: {total_jobs:.0f}")
        return {'direct': direct_jobs, 'indirect': indirect_jobs, 'induced': induced_jobs, 'total': total_jobs}

    def assess_workforce_transition_needs(self, region: str, skills_gap_data: dict) -> str:
        """Assesses needs for workforce development and skills transition."""
        # Placeholder for a more detailed assessment
        skill_shortages = skills_gap_data.get(region, {}).get('shortages', ['generic_technical_skills'])
        if not skill_shortages or 'none' in skill_shortages:
            assessment = "Low immediate need for targeted programs."
        else:
            assessment = f"High need for programs focusing on: {', '.join(skill_shortages)}."
        print(f"Workforce transition assessment for {region}: {assessment}")
        return assessment

if __name__ == '__main__':
    # Example Usage
    employment_data = {
        'SunValley': {'solar_jobs_per_mw_direct': 8, 'indirect_multiplier': 1.2, 'induced_multiplier': 0.6},
        'NorthState': {'solar_jobs_per_mw_direct': 6}
    }
    model = EmploymentModel(regional_employment_data=employment_data)
    model.estimate_job_creation(region='SunValley', new_solar_capacity_mw=100)
    
    skills_data = {'SunValley': {'shortages': ['PV installers', 'grid technicians']}}
    model.assess_workforce_transition_needs(region='SunValley', skills_gap_data=skills_data)
    model.assess_workforce_transition_needs(region='NorthState', skills_gap_data={})
