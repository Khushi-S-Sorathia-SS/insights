"""
Upload route for CSV dataset ingestion.
"""

import asyncio
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, File, UploadFile, Depends, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.database import get_db
from ..db.models import Dataset, Dashboard, DashboardComponent, ChatMessage
from ..semantic.semantic_layer import get_chart_rules

from ..models.session import UploadResponse
from ..storage.file_manager import file_manager
from ..storage.session_manager import session_manager
from ..utils.error_handler import SandboxError
from ..workflows.agent_planner import generate_analysis_code

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    db: AsyncSession = Depends(get_db)
) -> UploadResponse:
    # Validate display_name uniqueness
    existing_result = await db.execute(select(Dataset).filter(Dataset.display_name == display_name))
    if existing_result.scalars().first():
        raise HTTPException(status_code=400, detail=f"Workspace name '{display_name}' already exists. Please choose a different name.")

    # Use a dummy session_id for backward compatibility, but prioritize dataset_id
    temp_session_id = f"sess_{uuid4().hex}"
    
    metadata = await file_manager.save_uploaded_csv(file, temp_session_id, db, display_name=display_name)
    dataset_id = metadata.dataset_id

    default_chart_schemas: list[dict] = []
    auto_insights: str = ""

    file.file.seek(0)
    raw_data = file.file.read()
    
    chart_rules = await get_chart_rules(db)

    try:
        print(f"DEBUG: Starting initial analysis for dataset {dataset_id}...")
        result = await asyncio.to_thread(
            generate_analysis_code,
            "Create 3-4 visualizations to provide an initial overview of this dataset. Generate diverse charts according to the provided schema rules. Then provide a brief summary of key insights.",
            metadata,
            raw_data,
            chart_rules
        )
        auto_insights = result.get("output", "Could not generate initial dataset insights.")
        default_chart_schemas = result.get("chart_schemas", [])
        print(f"DEBUG: Analysis complete. Insights: {len(auto_insights)} chars, Charts: {len(default_chart_schemas)}")
    except SandboxError as e:
        print(f"DEBUG: Sandbox error during initial analysis: {e}")
        default_chart_schemas = []
        auto_insights = "Could not generate initial dataset insights."
    except Exception as e:
        print(f"DEBUG: Unexpected error during initial analysis: {e}")
        default_chart_schemas = []
        auto_insights = "Could not generate initial dataset insights."

    # Persist the dashboard and its components to the database
    from ..db.models import Dashboard, DashboardComponent
    import uuid
    
    ds_uuid = uuid.UUID(dataset_id)
    dashboard = Dashboard(
        dataset_id=ds_uuid,
        name=f"Workspace: {metadata.filename}",
        layout_json={}
    )
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    
    # Track the initial assistant message
    from ..db.models import ChatMessage
    initial_msg = ChatMessage(
        dataset_id=ds_uuid,
        role="assistant",
        content=f"Ingestion complete. Dataset '{metadata.filename}' has been indexed and workspace established. I am ready for advanced analytical queries.",
        created_at=datetime.utcnow()
    )
    db.add(initial_msg)

    # Add default widgets with suggested sizing
    current_y = 0
    row_height = 0
    
    for i, schema in enumerate(default_chart_schemas):
        w = schema.get("w", 6)
        h = schema.get("h", 4)
        
        # Calculate grid position
        x = (i % 2) * 6
        y = (i // 2) * 4 # This is the old way, let's keep it but make it smarter
        
        # If we start a new row, update our current_y tracker
        if i > 0 and i % 2 == 0:
            current_y += row_height
            row_height = h
        else:
            row_height = max(row_height, h)

        component = DashboardComponent(
            dashboard_id=dashboard.id,
            position={"x": x, "y": (i // 2) * 4, "w": w, "h": h},
            component_type="chart",
            chart_schema=schema
        )
        db.add(component)
        
    if auto_insights:
        # Place insight below everything else
        # Max Y for charts is roughly (len // 2) * 4 + max_h
        final_y = ((len(default_chart_schemas) + 1) // 2) * 4
        
        insight_component = DashboardComponent(
            dashboard_id=dashboard.id,
            position={"x": 0, "y": final_y, "w": 12, "h": 3},
            component_type="insight",
            chart_schema={"content": auto_insights}
        )
        db.add(insight_component)
        
    await db.commit()

    return UploadResponse(
        session_id=dataset_id, # Use dataset_id as the primary session identifier
        dashboard_id=str(dashboard.id),
        message="Upload successful",
        metadata=metadata,
        default_chart_schemas=default_chart_schemas,
        auto_insights=auto_insights,
    )
