import { useNavigate } from 'react-router-dom';
import { useGlobalState, updateProcessState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const DrivesAwayPage = () => {
  const navigate = useNavigate();
  const { processState } = useGlobalState();

  if (!processState.dry_completed) {
    return (
      <Card title="Drives away" hint="Waiting for dry...">
        <div className="animate-spin text-2xl">Loading...</div>
        <p>{processState.waitCondition.readableLabel}</p>
      </Card>
    );
  }

  const handleProceed = () => {
    updateProcessState({ drives_away_completed: true });
    navigate('/customer/complete');
  };

  return (
    <Card title="Drives away" hint="Page for BPMN task 'Drives away' (wait-then-write).">
      <Button onClick={handleProceed}>Proceed</Button>
    </Card>
  );
};