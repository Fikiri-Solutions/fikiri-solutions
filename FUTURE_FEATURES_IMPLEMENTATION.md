# 🛠️ Future Features Implementation Guide

## Dry-Run Everywhere

### Implementation Overview
Every new automation rule should support "simulate" mode and show "would have triggered N times in last 7 days."

### Backend Implementation

```python
class DryRunEngine:
    """Engine for simulating automation rules without executing actions."""
    
    def __init__(self, db_optimizer):
        self.db_optimizer = db_optimizer
    
    def simulate_rule(self, rule_id: int, days_back: int = 7) -> Dict[str, Any]:
        """Simulate automation rule execution for specified period."""
        try:
            # Get rule details
            rule = self._get_rule_details(rule_id)
            if not rule:
                return {'success': False, 'error': 'Rule not found'}
            
            # Get historical data for simulation
            historical_data = self._get_historical_data(rule['user_id'], days_back)
            
            # Simulate rule execution
            simulation_results = []
            trigger_count = 0
            
            for data_point in historical_data:
                if self._check_trigger_conditions(rule, data_point):
                    trigger_count += 1
                    
                    # Simulate action (without executing)
                    simulated_action = self._simulate_action(rule, data_point)
                    simulation_results.append({
                        'timestamp': data_point['timestamp'],
                        'trigger_data': data_point,
                        'simulated_action': simulated_action,
                        'would_execute': True
                    })
            
            return {
                'success': True,
                'rule_id': rule_id,
                'simulation_period_days': days_back,
                'total_triggers': trigger_count,
                'simulation_results': simulation_results,
                'summary': {
                    'would_trigger_count': trigger_count,
                    'average_per_day': trigger_count / days_back,
                    'last_trigger': simulation_results[-1]['timestamp'] if simulation_results else None
                }
            }
            
        except Exception as e:
            logger.error(f"Dry run simulation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_historical_data(self, user_id: int, days_back: int) -> List[Dict[str, Any]]:
        """Get historical data for simulation."""
        # Get emails from last N days
        emails = self.db_optimizer.execute_query(
            """
            SELECT id, sender_email, subject, body, received_at, labels
            FROM emails 
            WHERE user_id = ? AND received_at >= datetime('now', '-{} days')
            ORDER BY received_at DESC
            """.format(days_back),
            (user_id,),
            fetch=True
        )
        
        # Get leads from last N days
        leads = self.db_optimizer.execute_query(
            """
            SELECT id, email, name, stage, created_at, last_activity
            FROM leads 
            WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
            ORDER BY created_at DESC
            """.format(days_back),
            (user_id,),
            fetch=True
        )
        
        # Combine and format data
        historical_data = []
        
        for email in emails:
            historical_data.append({
                'type': 'email',
                'timestamp': email['received_at'],
                'data': email
            })
        
        for lead in leads:
            historical_data.append({
                'type': 'lead',
                'timestamp': lead['created_at'],
                'data': lead
            })
        
        return sorted(historical_data, key=lambda x: x['timestamp'])
    
    def _simulate_action(self, rule: Dict[str, Any], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate action execution without performing it."""
        action_type = rule['action_type']
        
        if action_type == 'auto_reply':
            return {
                'action': 'send_email',
                'recipient': trigger_data['data']['sender_email'],
                'template': rule['action_parameters']['template'],
                'subject': rule['action_parameters']['subject']
            }
        elif action_type == 'apply_label':
            return {
                'action': 'apply_label',
                'email_id': trigger_data['data']['id'],
                'label': rule['action_parameters']['label']
            }
        elif action_type == 'update_lead_stage':
            return {
                'action': 'update_lead_stage',
                'lead_id': trigger_data['data']['id'],
                'new_stage': rule['action_parameters']['stage']
            }
        
        return {'action': 'unknown', 'details': 'Action type not supported'}
```

### API Endpoints

```python
@app.route('/api/automation/simulate', methods=['POST'])
@handle_api_errors
def api_simulate_automation():
    """Simulate automation rule execution."""
    data = request.get_json()
    rule_id = data.get('rule_id')
    days_back = data.get('days_back', 7)
    
    if not rule_id:
        return create_error_response("Rule ID required", 400, "MISSING_RULE_ID")
    
    result = dry_run_engine.simulate_rule(int(rule_id), int(days_back))
    
    if result['success']:
        return create_success_response(result, "Simulation completed")
    else:
        return create_error_response(result['error'], 400, "SIMULATION_FAILED")

@app.route('/api/automation/simulate-new', methods=['POST'])
@handle_api_errors
def api_simulate_new_automation():
    """Simulate new automation rule before creating."""
    data = request.get_json()
    rule_data = data.get('rule_data')
    days_back = data.get('days_back', 7)
    
    if not rule_data:
        return create_error_response("Rule data required", 400, "MISSING_RULE_DATA")
    
    # Create temporary rule for simulation
    temp_rule_id = dry_run_engine.create_temp_rule(rule_data)
    
    # Simulate the rule
    result = dry_run_engine.simulate_rule(temp_rule_id, int(days_back))
    
    # Clean up temporary rule
    dry_run_engine.delete_temp_rule(temp_rule_id)
    
    if result['success']:
        return create_success_response(result, "New rule simulation completed")
    else:
        return create_error_response(result['error'], 400, "SIMULATION_FAILED")
```

### Frontend Implementation

```tsx
// DryRunSimulation component
interface DryRunSimulationProps {
    ruleId: number;
    onSimulationComplete: (results: SimulationResults) => void;
}

const DryRunSimulation: React.FC<DryRunSimulationProps> = ({ ruleId, onSimulationComplete }) => {
    const [isSimulating, setIsSimulating] = useState(false);
    const [simulationResults, setSimulationResults] = useState<SimulationResults | null>(null);
    const [daysBack, setDaysBack] = useState(7);
    
    const runSimulation = async () => {
        setIsSimulating(true);
        
        try {
            const response = await apiClient.post('/automation/simulate', {
                rule_id: ruleId,
                days_back: daysBack
            });
            
            setSimulationResults(response.data);
            onSimulationComplete(response.data);
        } catch (error) {
            console.error('Simulation failed:', error);
        } finally {
            setIsSimulating(false);
        }
    };
    
    return (
        <div className="dry-run-simulation">
            <div className="simulation-controls">
                <label>
                    Simulate last {daysBack} days:
                    <input
                        type="number"
                        value={daysBack}
                        onChange={(e) => setDaysBack(parseInt(e.target.value))}
                        min="1"
                        max="30"
                    />
                </label>
                <button onClick={runSimulation} disabled={isSimulating}>
                    {isSimulating ? 'Simulating...' : 'Run Simulation'}
                </button>
            </div>
            
            {simulationResults && (
                <div className="simulation-results">
                    <h3>Simulation Results</h3>
                    <div className="summary">
                        <p>Would have triggered: <strong>{simulationResults.summary.would_trigger_count}</strong> times</p>
                        <p>Average per day: <strong>{simulationResults.summary.average_per_day.toFixed(1)}</strong></p>
                        <p>Last trigger: <strong>{simulationResults.summary.last_trigger || 'Never'}</strong></p>
                    </div>
                    
                    <div className="detailed-results">
                        <h4>Detailed Results</h4>
                        {simulationResults.simulation_results.map((result, index) => (
                            <div key={index} className="simulation-result-item">
                                <p><strong>{result.timestamp}</strong></p>
                                <p>Action: {result.simulated_action.action}</p>
                                {result.simulated_action.recipient && (
                                    <p>To: {result.simulated_action.recipient}</p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// Usage in automation rule creation
const AutomationRuleForm: React.FC = () => {
    const [ruleData, setRuleData] = useState<AutomationRule>({});
    const [showSimulation, setShowSimulation] = useState(false);
    
    return (
        <div className="automation-rule-form">
            {/* Rule configuration form */}
            
            <div className="simulation-section">
                <button onClick={() => setShowSimulation(!showSimulation)}>
                    {showSimulation ? 'Hide' : 'Show'} Simulation
                </button>
                
                {showSimulation && (
                    <DryRunSimulation
                        ruleId={ruleData.id || 0}
                        onSimulationComplete={(results) => {
                            console.log('Simulation completed:', results);
                        }}
                    />
                )}
            </div>
        </div>
    );
};
```

## User-Visible Action Log

### Implementation Overview
Per rule, per day counts + last 10 actions with status (success/fail + reason). This reduces support tickets dramatically.

### Backend Implementation

```python
class ActionLogManager:
    """Manages user-visible action logs for automation rules."""
    
    def __init__(self, db_optimizer):
        self.db_optimizer = db_optimizer
        self._initialize_action_log_tables()
    
    def _initialize_action_log_tables(self):
        """Initialize action log tables."""
        self.db_optimizer.execute_query("""
            CREATE TABLE IF NOT EXISTS user_action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rule_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_contact TEXT NOT NULL,
                status TEXT NOT NULL, -- 'success', 'failed', 'skipped'
                reason TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details JSON,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (rule_id) REFERENCES automation_rules (id) ON DELETE CASCADE
            )
        """, fetch=False)
        
        # Create indexes for performance
        self.db_optimizer.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_user_action_logs_user_rule 
            ON user_action_logs (user_id, rule_id, executed_at)
        """, fetch=False)
    
    def log_action(self, user_id: int, rule_id: int, action_type: str, 
                   target_contact: str, status: str, reason: str = None, 
                   details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Log automation action for user visibility."""
        try:
            self.db_optimizer.execute_query(
                """
                INSERT INTO user_action_logs 
                (user_id, rule_id, action_type, target_contact, status, reason, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, rule_id, action_type, target_contact, status, reason, 
                 json.dumps(details) if details else None),
                fetch=False
            )
            
            return {'success': True, 'message': 'Action logged successfully'}
            
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_rule_action_summary(self, user_id: int, rule_id: int, days: int = 30) -> Dict[str, Any]:
        """Get action summary for a specific rule."""
        try:
            # Get daily counts
            daily_counts = self.db_optimizer.execute_query(
                """
                SELECT 
                    DATE(executed_at) as day,
                    status,
                    COUNT(*) as count
                FROM user_action_logs 
                WHERE user_id = ? AND rule_id = ? 
                AND executed_at >= datetime('now', '-{} days')
                GROUP BY DATE(executed_at), status
                ORDER BY day DESC
                """.format(days),
                (user_id, rule_id),
                fetch=True
            )
            
            # Get last 10 actions
            last_actions = self.db_optimizer.execute_query(
                """
                SELECT 
                    action_type,
                    target_contact,
                    status,
                    reason,
                    executed_at,
                    details
                FROM user_action_logs 
                WHERE user_id = ? AND rule_id = ?
                ORDER BY executed_at DESC
                LIMIT 10
                """,
                (user_id, rule_id),
                fetch=True
            )
            
            # Calculate totals
            total_actions = sum(row['count'] for row in daily_counts)
            success_count = sum(row['count'] for row in daily_counts if row['status'] == 'success')
            failed_count = sum(row['count'] for row in daily_counts if row['status'] == 'failed')
            
            return {
                'success': True,
                'data': {
                    'rule_id': rule_id,
                    'period_days': days,
                    'summary': {
                        'total_actions': total_actions,
                        'success_count': success_count,
                        'failed_count': failed_count,
                        'success_rate': (success_count / total_actions * 100) if total_actions > 0 else 0
                    },
                    'daily_counts': daily_counts,
                    'last_actions': last_actions
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get rule action summary: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_action_summary(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get action summary for all user rules."""
        try:
            # Get rule summaries
            rule_summaries = self.db_optimizer.execute_query(
                """
                SELECT 
                    rule_id,
                    COUNT(*) as total_actions,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
                FROM user_action_logs 
                WHERE user_id = ? 
                AND executed_at >= datetime('now', '-{} days')
                GROUP BY rule_id
                ORDER BY total_actions DESC
                """.format(days),
                (user_id,),
                fetch=True
            )
            
            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'period_days': days,
                    'rule_summaries': rule_summaries
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get user action summary: {e}")
            return {'success': False, 'error': str(e)}
```

### API Endpoints

```python
@app.route('/api/automation/action-log/<int:rule_id>', methods=['GET'])
@handle_api_errors
def api_get_rule_action_log(rule_id):
    """Get action log for specific rule."""
    user_id = request.args.get('user_id')
    days = int(request.args.get('days', 30))
    
    if not user_id:
        return create_error_response("User ID required", 400, "MISSING_USER_ID")
    
    result = action_log_manager.get_rule_action_summary(int(user_id), rule_id, days)
    
    if result['success']:
        return create_success_response(result['data'], "Action log retrieved")
    else:
        return create_error_response(result['error'], 400, "ACTION_LOG_FAILED")

@app.route('/api/automation/action-log/summary', methods=['GET'])
@handle_api_errors
def api_get_user_action_log_summary():
    """Get action log summary for all user rules."""
    user_id = request.args.get('user_id')
    days = int(request.args.get('days', 30))
    
    if not user_id:
        return create_error_response("User ID required", 400, "MISSING_USER_ID")
    
    result = action_log_manager.get_user_action_summary(int(user_id), days)
    
    if result['success']:
        return create_success_response(result['data'], "Action log summary retrieved")
    else:
        return create_error_response(result['error'], 400, "ACTION_LOG_FAILED")
```

### Frontend Implementation

```tsx
// ActionLog component
interface ActionLogProps {
    ruleId: number;
    userId: number;
}

const ActionLog: React.FC<ActionLogProps> = ({ ruleId, userId }) => {
    const [actionLog, setActionLog] = useState<ActionLogData | null>(null);
    const [loading, setLoading] = useState(true);
    const [days, setDays] = useState(30);
    
    useEffect(() => {
        fetchActionLog();
    }, [ruleId, userId, days]);
    
    const fetchActionLog = async () => {
        setLoading(true);
        try {
            const response = await apiClient.get(`/automation/action-log/${ruleId}`, {
                params: { user_id: userId, days }
            });
            setActionLog(response.data);
        } catch (error) {
            console.error('Failed to fetch action log:', error);
        } finally {
            setLoading(false);
        }
    };
    
    if (loading) return <div>Loading action log...</div>;
    if (!actionLog) return <div>No action log data available</div>;
    
    return (
        <div className="action-log">
            <div className="action-log-header">
                <h3>Action Log</h3>
                <div className="period-selector">
                    <label>
                        Last {days} days:
                        <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
                            <option value={7}>7 days</option>
                            <option value={30}>30 days</option>
                            <option value={90}>90 days</option>
                        </select>
                    </label>
                </div>
            </div>
            
            <div className="action-summary">
                <div className="summary-stats">
                    <div className="stat">
                        <span className="label">Total Actions:</span>
                        <span className="value">{actionLog.summary.total_actions}</span>
                    </div>
                    <div className="stat">
                        <span className="label">Success Rate:</span>
                        <span className="value">{actionLog.summary.success_rate.toFixed(1)}%</span>
                    </div>
                    <div className="stat">
                        <span className="label">Successful:</span>
                        <span className="value success">{actionLog.summary.success_count}</span>
                    </div>
                    <div className="stat">
                        <span className="label">Failed:</span>
                        <span className="value error">{actionLog.summary.failed_count}</span>
                    </div>
                </div>
            </div>
            
            <div className="daily-counts">
                <h4>Daily Activity</h4>
                <div className="daily-chart">
                    {actionLog.daily_counts.map((day, index) => (
                        <div key={index} className="daily-bar">
                            <div className="day-label">{day.day}</div>
                            <div className="day-stats">
                                <div className="success-bar" style={{ width: `${day.success_count * 10}px` }}>
                                    {day.success_count}
                                </div>
                                <div className="failed-bar" style={{ width: `${day.failed_count * 10}px` }}>
                                    {day.failed_count}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
            
            <div className="recent-actions">
                <h4>Recent Actions</h4>
                <div className="actions-list">
                    {actionLog.last_actions.map((action, index) => (
                        <div key={index} className={`action-item ${action.status}`}>
                            <div className="action-time">{action.executed_at}</div>
                            <div className="action-details">
                                <span className="action-type">{action.action_type}</span>
                                <span className="target-contact">{action.target_contact}</span>
                                <span className={`status ${action.status}`}>{action.status}</span>
                                {action.reason && (
                                    <span className="reason">{action.reason}</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

// Usage in automation dashboard
const AutomationDashboard: React.FC = () => {
    const [rules, setRules] = useState<AutomationRule[]>([]);
    const [selectedRule, setSelectedRule] = useState<AutomationRule | null>(null);
    
    return (
        <div className="automation-dashboard">
            <div className="rules-list">
                {rules.map(rule => (
                    <div key={rule.id} className="rule-item" onClick={() => setSelectedRule(rule)}>
                        <h3>{rule.name}</h3>
                        <p>{rule.description}</p>
                        <span className={`status ${rule.status}`}>{rule.status}</span>
                    </div>
                ))}
            </div>
            
            {selectedRule && (
                <div className="rule-details">
                    <h2>{selectedRule.name}</h2>
                    <ActionLog ruleId={selectedRule.id} userId={selectedRule.user_id} />
                </div>
            )}
        </div>
    );
};
```

## Implementation Checklist

### Dry-Run Everywhere
- [ ] Backend simulation engine
- [ ] Historical data retrieval
- [ ] Trigger condition checking
- [ ] Action simulation (without execution)
- [ ] API endpoints for simulation
- [ ] Frontend simulation component
- [ ] Integration with rule creation
- [ ] Performance optimization for large datasets

### User-Visible Action Log
- [ ] Action logging database schema
- [ ] Action logging manager
- [ ] Daily count aggregation
- [ ] Recent actions retrieval
- [ ] API endpoints for action logs
- [ ] Frontend action log component
- [ ] Dashboard integration
- [ ] Export functionality

### Performance Considerations
- [ ] Database indexing for fast queries
- [ ] Caching for frequently accessed data
- [ ] Pagination for large result sets
- [ ] Background processing for heavy simulations
- [ ] Rate limiting for simulation requests
- [ ] Monitoring and alerting

### User Experience
- [ ] Intuitive simulation interface
- [ ] Clear action log visualization
- [ ] Responsive design for mobile
- [ ] Accessibility compliance
- [ ] Error handling and recovery
- [ ] Loading states and progress indicators

---

**Remember**: These features significantly reduce support tickets by giving users visibility into what their automations are doing. The dry-run feature builds confidence, while the action log provides transparency and debugging capabilities.
