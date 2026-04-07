"""Tests for the batch reviews API."""

from app.models.batch_review import BatchReview, ImprovementProposal


def test_list_batch_reviews_empty(client):
    resp = client.get("/api/v1/batch-reviews")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_batch_reviews_with_data(db, client):
    review = BatchReview(
        trigger_reason="manual",
        batch_size=10,
        status="completed",
        strategy_brief="Test brief",
    )
    db.add(review)
    db.commit()

    resp = client.get("/api/v1/batch-reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trigger_reason"] == "manual"
    assert data[0]["batch_size"] == 10
    assert data[0]["status"] == "completed"
    assert data[0]["proposals_count"] == 0


def test_get_batch_review_detail(db, client):
    review = BatchReview(
        trigger_reason="25_leads",
        batch_size=25,
        status="completed",
        executor_draft="Draft text",
        reviewer_verdict="validated",
        strategy_brief="Strategy brief",
    )
    db.add(review)
    db.flush()

    proposal = ImprovementProposal(
        batch_review_id=review.id,
        category="scoring",
        description="Adjust weights",
        impact="high",
        confidence="medium",
        status="pending",
    )
    db.add(proposal)
    db.commit()

    resp = client.get(f"/api/v1/batch-reviews/{review.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trigger_reason"] == "25_leads"
    assert data["batch_size"] == 25
    assert data["executor_draft"] == "Draft text"
    assert data["reviewer_verdict"] == "validated"
    assert len(data["proposals"]) == 1
    assert data["proposals"][0]["category"] == "scoring"


def test_get_batch_review_not_found(client):
    resp = client.get("/api/v1/batch-reviews/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_generate_batch_review(client, monkeypatch):
    class FakeResult:
        id = "fake-task-id"

    class FakeTask:
        def delay(self):
            return FakeResult()

    monkeypatch.setattr(
        "app.api.v1.batch_reviews.task_generate_batch_review_manual",
        FakeTask(),
        raising=False,
    )
    # The endpoint imports the task lazily, so we patch at the module where it's used
    import app.workers.batch_review_tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "task_generate_batch_review_manual", FakeTask())

    resp = client.post("/api/v1/batch-reviews/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "task_id" in data


def test_approve_proposal(db, client):
    review = BatchReview(
        trigger_reason="manual",
        batch_size=5,
        status="completed",
    )
    db.add(review)
    db.flush()

    proposal = ImprovementProposal(
        batch_review_id=review.id,
        category="outreach",
        description="Better subject lines",
        impact="medium",
        confidence="high",
        status="pending",
    )
    db.add(proposal)
    db.commit()

    resp = client.post(f"/api/v1/batch-reviews/proposals/{proposal.id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["approved_by"] == "operator"


def test_approve_proposal_not_found(client):
    resp = client.post(
        "/api/v1/batch-reviews/proposals/00000000-0000-0000-0000-000000000000/approve"
    )
    assert resp.status_code == 404


def test_apply_proposal(db, client):
    review = BatchReview(
        trigger_reason="manual",
        batch_size=5,
        status="completed",
    )
    db.add(review)
    db.flush()

    proposal = ImprovementProposal(
        batch_review_id=review.id,
        category="scoring",
        description="Raise threshold",
        impact="high",
        confidence="high",
        status="approved",
        approved_by="operator",
    )
    db.add(proposal)
    db.commit()

    resp = client.post(f"/api/v1/batch-reviews/proposals/{proposal.id}/apply")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "applied"
    assert data["applied_at"] is not None


def test_apply_proposal_not_approved(db, client):
    review = BatchReview(
        trigger_reason="manual",
        batch_size=5,
        status="completed",
    )
    db.add(review)
    db.flush()

    proposal = ImprovementProposal(
        batch_review_id=review.id,
        category="scoring",
        description="Pending proposal",
        impact="low",
        confidence="low",
        status="pending",
    )
    db.add(proposal)
    db.commit()

    resp = client.post(f"/api/v1/batch-reviews/proposals/{proposal.id}/apply")
    assert resp.status_code == 404


def test_reject_proposal(db, client):
    review = BatchReview(
        trigger_reason="manual",
        batch_size=5,
        status="completed",
    )
    db.add(review)
    db.flush()

    proposal = ImprovementProposal(
        batch_review_id=review.id,
        category="outreach",
        description="Bad idea",
        impact="low",
        confidence="low",
        status="pending",
    )
    db.add(proposal)
    db.commit()

    resp = client.post(f"/api/v1/batch-reviews/proposals/{proposal.id}/reject")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"


def test_reject_proposal_not_found(client):
    resp = client.post(
        "/api/v1/batch-reviews/proposals/00000000-0000-0000-0000-000000000000/reject"
    )
    assert resp.status_code == 404
