import React, { useState } from 'react';
import { useGlobalState } from '../state/globalState';

export const LoginPage: React.FC = () => {
  const [name, setName] = useState('');
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const { login } = useGlobalState();
  const { defaultRoutesPerRole, roles } = useGlobalState();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name && selectedRole) {
      login(name, selectedRole);
      window.location.href = defaultRoutesPerRole[selectedRole];
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Card>
        <Typography variant="h5" component="h2">
          {useGlobalState().project}
        </Typography>
        <TextField
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          margin="normal"
          required
        />
        <Stack direction="row" spacing={1}>
          {roles.map((role) => (
            <Button
              key={role.value}
              variant={selectedRole === role.value ? 'primary' : 'secondary'}
              onClick={() => setSelectedRole(role.value)}
            >
              {role.display}
            </Button>
          ))}
        </Stack>
        <Button
          type="submit"
          variant="contained"
          color="primary"
          disabled={!name || !selectedRole}
        >
          Enter
        </Button>
      </Card>
    </div>
  );
};